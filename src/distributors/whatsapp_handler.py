import asyncio
import hashlib
import hmac
from typing import Any

import httpx
import sentry_sdk
from loguru import logger


class WhatsAppHandler:
    """Maneja mensajes de WhatsApp via la API directa de Meta (WhatsApp Cloud API).

    Sin intermediario (BSP) como Twilio: llama directo a la Graph API de Meta
    con un token de acceso permanente sobre el numero de la WhatsApp Business
    Account. Se dejo de usar Twilio porque exige auto-recharge obligatorio o
    suspende la cuenta, ademas de cobrar su propio markup encima de la
    tarifa que ya cobra Meta -- yendo directo se paga solo lo que cobra
    Meta, facturado como una cuenta normal (sin minimo ni recargo forzado).

    A diferencia de Twilio (que espera TwiML embebido en la respuesta del
    webhook para contestar), la API de Meta no tiene ese mecanismo: recibir
    un mensaje (webhook) y responderlo son dos llamadas HTTP separadas.
    `process_webhook_event` hace las dos: procesa el evento entrante con
    `handle_message` y, si hay respuesta, la manda de vuelta con
    `send_message` -- el endpoint en main.py solo necesita reenviarle el
    payload y devolver 200 OK.
    """

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
        self._client: httpx.AsyncClient | None = None
        self._phone_number_id: str | None = None

        access_token = getattr(settings, "whatsapp_meta_access_token", None)
        phone_number_id = getattr(settings, "whatsapp_meta_phone_number_id", None)

        if access_token and phone_number_id:
            api_version = getattr(settings, "whatsapp_meta_api_version", None) or "v21.0"
            self._phone_number_id = phone_number_id
            self._client = httpx.AsyncClient(
                base_url=f"https://graph.facebook.com/{api_version}",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=20.0,
            )
            logger.info("WhatsApp handler inicializado con Meta Cloud API")
        else:
            logger.info("WhatsApp handler inicializado sin credenciales de Meta (modo desarrollo)")

    @property
    def is_configured(self) -> bool:
        return self._client is not None

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()

    @staticmethod
    def verify_webhook_signature(app_secret: str | None, body: bytes, signature_header: str | None) -> bool:
        """Valida `X-Hub-Signature-256` contra el cuerpo crudo del request.

        Meta firma cada webhook con el App Secret (no un token por numero
        como Twilio) para que nadie pueda mandar eventos falsos adivinando
        la URL -- sin esto, cualquiera podria dar de baja a cualquier
        numero de telefono con un POST directo."""

        if not app_secret:
            return True
        if not signature_header or not signature_header.startswith("sha256="):
            return False

        expected = hmac.new(app_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        provided = signature_header.removeprefix("sha256=")
        return hmac.compare_digest(expected, provided)

    @staticmethod
    def extract_inbound_message(payload: dict[str, Any]) -> tuple[str, str] | None:
        """Saca (remitente, texto) del payload anidado que manda Meta.

        Devuelve None para eventos que no son un mensaje de texto entrante
        (confirmaciones de entrega/lectura, reacciones, etc.) -- esos no
        necesitan respuesta."""

        try:
            entries = payload.get("entry") or []
            for entry in entries:
                for change in entry.get("changes") or []:
                    value = change.get("value") or {}
                    for message in value.get("messages") or []:
                        if message.get("type") != "text":
                            continue
                        sender = message.get("from")
                        text = (message.get("text") or {}).get("body")
                        if sender and text is not None:
                            return str(sender), str(text)
        except (AttributeError, TypeError):
            return None

        return None

    async def process_webhook_event(self, payload: dict[str, Any]) -> None:
        """Procesa un evento entrante recibido por webhook y responde si aplica.

        No propaga excepciones: un evento malformado o un error de la API
        de Meta no debe tumbar el endpoint del webhook."""

        try:
            extracted = self.extract_inbound_message(payload)
            if not extracted:
                return

            sender, body = extracted
            reply_text = await self.handle_message(sender, body)
            if reply_text:
                await self.send_message(sender, reply_text)
        except Exception as e:
            logger.error(f"Error procesando evento de WhatsApp: {e}")
            sentry_sdk.capture_exception(e)

    async def handle_message(self, from_number: str, body: str) -> str | None:
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
            result = handler(from_number)
            return await result if asyncio.iscoroutine(result) else result

        return await self._handle_selection(from_number, body)

    def _handle_start(self, from_number: str) -> str:
        text = "*EcoBrief Bolivia*\n\n"
        text += "Briefs de noticias bolivianas con menos ruido y segun tus preferencias.\n\n"
        text += "Selecciona las categorias que te interesan:\n\n"

        for key, cat in self.CATEGORIES.items():
            text += f"{key}. {cat['emoji']} {cat['name']}\n"

        text += "\n6. Todas\n\n"
        text += "Responde con los numeros, por ejemplo: 1,3 o 1 3\n"
        text += "Envia 6 para todas las categorias"
        return text

    def _handle_preferences(self, from_number: str) -> str:
        return self._handle_start(from_number)

    async def _handle_cancel(self, from_number: str) -> str:
        if self.db:
            await self.db.unsubscribe(from_number)

        return "Te has dado de baja de EcoBrief Bolivia. Para volver a suscribirte, envia Hola."

    def _handle_help(self, from_number: str) -> str:
        text = "*Ayuda EcoBrief Bolivia*\n\n"
        text += "Hola - Iniciar suscripcion\n"
        text += "1,2,3... - Seleccionar categorias\n"
        text += "6 - Todas las categorias\n"
        text += "preferencias - Cambiar categorias\n"
        text += "cancelar - Darse de baja\n"
        text += "ayuda - Ver esta ayuda"
        return text

    async def _handle_selection(self, from_number: str, body: str) -> str:
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
            await self.db.save_subscription(
                phone=from_number,
                channel="whatsapp",
                categories=categories,
                consent_accepted=True,
            )

        names = [
            f"{self.CATEGORIES[key]['emoji']} {self.CATEGORIES[key]['name']}"
            for key in sorted(selected_keys)
        ]

        text = "*Preferencias guardadas en EcoBrief Bolivia*\n\n"
        text += "Te enviare briefs de:\n"
        for name in names:
            text += f"- {name}\n"

        if self.settings:
            text += f"\nHorario: {self.settings.schedule_summary_morning}"

        return text

    async def send_message(self, to: str, message: str) -> bool:
        """Envia un mensaje de texto de WhatsApp via la Graph API de Meta.

        Solo entrega si el destinatario escribio primero dentro de las
        ultimas 24h (ventana de servicio gratis) o si se usa un template
        aprobado -- un texto libre fuera de esa ventana lo rechaza Meta."""

        if not self._client or not self._phone_number_id:
            logger.warning(f"WhatsApp (Meta) no configurado. Mensaje no enviado: {message[:50]}...")
            return False

        payload = {
            "messaging_product": "whatsapp",
            "to": self._normalize_number(to),
            "type": "text",
            "text": {"body": message},
        }

        try:
            response = await self._client.post(f"/{self._phone_number_id}/messages", json=payload)
            response.raise_for_status()
            logger.info(f"WhatsApp mensaje enviado a {to}")
            return True
        except Exception as e:
            logger.error(f"Error enviando WhatsApp: {e}")
            sentry_sdk.capture_exception(e)
            return False

    def _normalize_number(self, phone: str) -> str:
        """Meta espera el numero en formato E.164 sin el '+' inicial."""

        return phone.strip().lstrip("+").replace(" ", "").replace("-", "")

    async def send_daily_summary(self, to: str, news: list[dict]) -> bool:
        """Envia el resumen diario."""

        message = self._format_summary(news)
        return await self.send_message(to, message)

    def _format_summary(self, news: list[dict]) -> str:
        """Formatea el resumen para WhatsApp."""

        text = "*EcoBrief Bolivia - Brief del dia*\n\n"
        text += "Noticias locales resumidas con menos ruido.\n\n"

        for i, article in enumerate(news[:10], 1):
            text += f"{i}. *{article.get('title', '')}*\n"
            text += f"   {article.get('summary', '')}\n"
            if article.get("fact"):
                text += f"   Dato: {article.get('fact')}\n"
            text += "\n"

        text += "---\n"
        text += "preferencias | cancelar"
        return text
