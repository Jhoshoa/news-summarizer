from contextlib import suppress

from loguru import logger


class TelegramHandler:
    """Maneja el bot de Telegram."""

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
        self.app = None

        if settings and settings.telegram_bot_token:
            logger.info("Telegram handler inicializado")
        else:
            logger.info("Telegram handler inicializado sin token (modo desarrollo)")

    async def handle_message(self, update, context) -> str | None:
        """Procesa mensaje entrante."""

        if not update.message:
            return None

        text = update.message.text.strip().upper()
        chat_id = str(update.message.chat.id)

        handlers = {
            "/START": self._handle_start,
            "/AYUDA": self._handle_help,
            "/HELP": self._handle_help,
            "HOLA": self._handle_start,
            "INICIO": self._handle_start,
            "/PREFERENCIAS": self._handle_preferences,
            "/PREFERENCIA": self._handle_preferences,
            "/CANCELAR": self._handle_cancel,
            "/BAJA": self._handle_cancel,
        }

        handler = handlers.get(text)
        if handler:
            return await handler(update, context)

        return await self._handle_selection(update, context, chat_id, text)

    async def _handle_start(self, update, context) -> str:
        text = "*EcoBrief Bolivia*\n\n"
        text += "Briefs de noticias bolivianas con menos ruido y segun tus preferencias.\n\n"
        text += "Selecciona las categorias que te interesan:"

        await update.message.reply_text(text, parse_mode="Markdown")
        await self._show_categories(update)
        return text

    async def _show_categories(self, update) -> None:
        """Muestra botones de categorias."""

        try:
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        except ImportError:
            return

        keyboard = []
        for key, cat in self.CATEGORIES.items():
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"{cat['emoji']} {cat['name']}",
                        callback_data=f"cat_{key}",
                    )
                ]
            )
        keyboard.append([InlineKeyboardButton("Todas", callback_data="cat_todas")])

        with suppress(Exception):
            await update.message.reply_text(
                "Selecciona:",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

    async def _handle_preferences(self, update, context) -> str:
        await self._show_categories(update)
        return "Cambia tus preferencias"

    async def _handle_cancel(self, update, context) -> str:
        if self.db:
            chat_id = str(update.message.chat.id)
            await self.db.unsubscribe(chat_id)

        await update.message.reply_text(
            "Te has dado de baja de EcoBrief Bolivia. Para volver: /preferencias"
        )
        return "Dado de baja"

    async def _handle_help(self, update, context) -> str:
        text = "*Ayuda EcoBrief Bolivia*\n\n"
        text += "/start - Iniciar suscripcion\n"
        text += "/preferencias - Cambiar categorias\n"
        text += "/cancelar - Darse de baja\n"
        text += "/ayuda - Ver ayuda"

        await update.message.reply_text(text, parse_mode="Markdown")
        return text

    async def _handle_selection(self, update, context, chat_id: str, text: str) -> str:
        """Procesa seleccion de categorias."""

        import re

        selected_keys = {
            number
            for number in re.findall(r"\d+", text)
            if number in self.CATEGORIES or number == "6"
        }

        if not selected_keys:
            await update.message.reply_text("Seleccion invalida. Usa /preferencias")
            return "Seleccion invalida"

        if "6" in selected_keys:
            selected_keys = set(self.CATEGORIES.keys())

        categories = {self.CATEGORIES[key]["category"] for key in selected_keys}

        if self.db:
            await self.db.save_subscription(
                telegram_id=chat_id,
                channel="telegram",
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

        await update.message.reply_text(text, parse_mode="Markdown")
        return "Suscripcion guardada"

    async def send_message(self, chat_id: str, message: str) -> bool:
        """Envia mensaje."""

        if not self.app:
            logger.warning(f"Telegram no configurado. Mensaje: {message[:50]}...")
            return False

        try:
            await self.app.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="Markdown",
            )
            logger.info(f"Telegram mensaje enviado a {chat_id}")
            return True
        except Exception as e:
            logger.error(f"Error enviando Telegram: {e}")
            return False

    async def send_daily_summary(self, chat_id: str, news: list[dict]) -> bool:
        """Envia el resumen diario."""

        message = self._format_summary(news)
        return await self.send_message(chat_id, message)

    def _format_summary(self, news: list[dict]) -> str:
        """Formatea el resumen para Telegram."""

        text = "*EcoBrief Bolivia - Brief del dia*\n\n"
        text += "Noticias locales resumidas con menos ruido.\n\n"

        for i, article in enumerate(news[:10], 1):
            text += f"{i}. *{article.get('title', '')}*\n"
            text += f"   {article.get('summary', '')}\n"
            if article.get("fact"):
                text += f"   Dato: {article.get('fact')}\n"
            text += "\n"

        text += "---\n"
        text += "/preferencias | /cancelar"
        return text
