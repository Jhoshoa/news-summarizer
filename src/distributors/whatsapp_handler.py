import asyncio

from loguru import logger


class WhatsAppHandler:
    """Maneja mensajes de WhatsApp via Twilio."""

    CATEGORIES = {
        "1": {"name": "Economia", "emoji": "$", "category": "economia"},
        "2": {"name": "Politica", "emoji": "#", "category": "politica"},
        "3": {"name": "Deportes", "emoji": "*", "category": "deportes"},
        "4": {"name": "Tecnologia", "emoji": "@", "category": "tecnologia"},
        "5": {"name": "Entretenimiento", "emoji": "+", "category": "entretenimiento"},
    }

    def __init__(self, db_repository=None, settings=None):
        self.db = db_repository
        self.settings = settings
        self.client = None

        if settings and settings.twilio_account_sid:
            try:
                from twilio.rest import Client

                self.client = Client(
                    settings.twilio_account_sid, settings.twilio_auth_token
                )
                logger.info("WhatsApp handler inicializado con Twilio")
            except ImportError:
                logger.warning("Twilio no esta instalado")
        else:
            logger.info("WhatsApp handler inicializado sin Twilio (modo desarrollo)")

    def handle_message(self, from_number: str, body: str) -> str | None:
        """Procesa mensaje entrante."""

        if not body:
            return self._handle_help(from_number)

        body = body.strip().upper()
        handlers = {
            "HOLA": self._handle_start,
            "HI": self._handle_start,
            "START": self._handle_start,
            "INICIO": self._handle_start,
            "/PREFERENCIAS": self._handle_preferences,
            "/PREFERENCIA": self._handle_preferences,
            "PREFERENCIAS": self._handle_preferences,
            "PREFERENCIA": self._handle_preferences,
            "/CANCELAR": self._handle_cancel,
            "/BAJA": self._handle_cancel,
            "CANCELAR": self._handle_cancel,
            "BAJA": self._handle_cancel,
            "/AYUDA": self._handle_help,
            "/HELP": self._handle_help,
            "AYUDA": self._handle_help,
            "HELP": self._handle_help,
        }

        handler = handlers.get(body)
        if handler:
            return handler(from_number)

        return self._handle_selection(from_number, body)

    def _handle_start(self, from_number: str) -> str:
        text = "*NewsDaily Bolivia*\n\n"
        text += "Resumen de noticias diarias de Bolivia\n\n"
        text += "Selecciona las categorias que te interesan:\n\n"

        for key, cat in self.CATEGORIES.items():
            text += f"{key}. {cat['emoji']} {cat['name']}\n"

        text += "\n6. Todas\n\n"
        text += "Responde con los numeros, por ejemplo: 1,3 o 1 3\n"
        text += "Envia 6 para todas las categorias"
        return text

    def _handle_preferences(self, from_number: str) -> str:
        return self._handle_start(from_number)

    def _handle_cancel(self, from_number: str) -> str:
        if self.db:
            asyncio.create_task(self.db.unsubscribe(from_number))

        return "Te has dado de baja. Para volver a suscribirte, envia Hola."

    def _handle_help(self, from_number: str) -> str:
        text = "*Ayuda*\n\n"
        text += "Hola - Iniciar suscripcion\n"
        text += "1,2,3... - Seleccionar categorias\n"
        text += "6 - Todas las categorias\n"
        text += "preferencias - Cambiar categorias\n"
        text += "cancelar - Darse de baja\n"
        text += "ayuda - Ver esta ayuda"
        return text

    def _handle_selection(self, from_number: str, body: str) -> str:
        import re

        selected_keys = {
            number
            for number in re.findall(r"\d+", body)
            if number in self.CATEGORIES or number == "6"
        }

        if not selected_keys:
            return "Seleccion invalida. Envia preferencias para ver opciones."

        if "6" in selected_keys:
            selected_keys = set(self.CATEGORIES.keys())

        categories = {self.CATEGORIES[key]["category"] for key in selected_keys}

        if self.db:
            asyncio.create_task(
                self.db.save_subscription(
                    phone=from_number,
                    channel="whatsapp",
                    categories=categories,
                )
            )

        names = [
            f"{self.CATEGORIES[key]['emoji']} {self.CATEGORIES[key]['name']}"
            for key in sorted(selected_keys)
        ]

        text = "*Guardado!*\n\n"
        text += "Te enviare resumenes de:\n"
        for name in names:
            text += f"- {name}\n"

        if self.settings:
            text += f"\nHorario: {self.settings.schedule_summary_morning}"

        return text

    def send_message(self, to: str, message: str) -> bool:
        """Envia mensaje de WhatsApp."""

        if not self.client:
            logger.warning(
                f"Twilio no configurado. Mensaje no enviado: {message[:50]}..."
            )
            return False

        if not self.settings or not self.settings.twilio_phone_number:
            logger.error("Twilio phone number no configurado")
            return False

        try:
            self.client.messages.create(
                from_=self.settings.twilio_phone_number,
                body=message,
                to=f"whatsapp:{to}",
            )
            logger.info(f"WhatsApp mensaje enviado a {to}")
            return True
        except Exception as e:
            logger.error(f"Error enviando WhatsApp: {e}")
            return False

    def send_daily_summary(self, to: str, news: list[dict]) -> bool:
        """Envia el resumen diario."""

        message = self._format_summary(news)
        return self.send_message(to, message)

    def _format_summary(self, news: list[dict]) -> str:
        """Formatea el resumen para WhatsApp."""

        text = "*Resumen de Hoy - Bolivia*\n\n"

        for i, article in enumerate(news[:10], 1):
            text += f"{i}. *{article.get('title', '')}*\n"
            text += f"   {article.get('summary', '')}\n"
            if article.get("fact"):
                text += f"   Dato: {article.get('fact')}\n"
            text += "\n"

        text += "---\n"
        text += "preferencias | cancelar"
        return text
