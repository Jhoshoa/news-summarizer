from typing import Optional
from loguru import logger


class TelegramHandler:
    """Maneja el bot de Telegram."""

    CATEGORIES = {
        "1": {"name": "Economía", "emoji": "💰"},
        "2": {"name": "Política", "emoji": "🏛️"},
        "3": {"name": "Deportes", "emoji": "⚽"},
        "4": {"name": "Tecnología", "emoji": "💻"},
        "5": {"name": "Entretenimiento", "emoji": "🎬"},
    }

    def __init__(self, db_repository=None, settings=None):
        self.db = db_repository
        self.settings = settings
        self.app = None

        if settings and settings.telegram_bot_token:
            logger.info("Telegram handler inicializado")
        else:
            logger.info("Telegram handler inicializado sin token (modo desarrollo)")

    async def handle_message(self, update, context) -> Optional[str]:
        """Procesa mensaje entrante."""

        if not update.message:
            return

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
        text = "📰 *NewsDaily Bolivia* 🇧🇴\n\n"
        text += "Resumen de noticias diarias de Bolivia\n\n"
        text += "Selecciona las categorías que te interesan:"

        await update.message.reply_text(text, parse_mode="Markdown")
        await self._show_categories(update)

        return text

    async def _show_categories(self, update):
        """Muestra botones de categorías."""

        try:
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        except ImportError:
            return

        keyboard = []
        for key, cat in self.CATEGORIES.items():
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"{cat['emoji']} {cat['name']}", callback_data=f"cat_{key}"
                    )
                ]
            )
        keyboard.append([InlineKeyboardButton("✅ Todas", callback_data="cat_todas")])

        try:
            await update.message.reply_text(
                "Selecciona:", reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except:
            pass

    async def _handle_preferences(self, update, context) -> str:
        await self._show_categories(update)
        return "Cambia tus preferencias"

    async def _handle_cancel(self, update, context) -> str:
        if self.db:
            chat_id = str(update.message.chat.id)
            await self.db.unsubscribe(chat_id)

        await update.message.reply_text(
            "✅ Te has dado de baja.\n\nPara volver: /preferencias"
        )
        return "Dado de baja"

    async def _handle_help(self, update, context) -> str:
        text = "📖 *Ayuda*\n\n"
        text += "/start - Iniciar suscripción\n"
        text += "/preferencias - Cambiar categorías\n"
        text += "/cancelar - Darse de baja\n"
        text += "/ayuda - Ver ayuda"

        await update.message.reply_text(text, parse_mode="Markdown")
        return text

    async def _handle_selection(self, update, context, chat_id: str, text: str) -> str:
        """Procesa selección de categorías."""

        import re

        numbers = re.findall(r"\d+", text)

        valid = set()
        for n in numbers:
            if n in self.CATEGORIES or n == "6":
                valid.add(n)

        if not valid:
            await update.message.reply_text("Selección inválida. Usa /preferencias")
            return None

        if "6" in valid:
            categories = set(self.CATEGORIES.keys())
        else:
            categories = valid

        if self.db:
            await self.db.save_subscription(
                telegram_id=chat_id, channel="telegram", categories=categories
            )

        names = []
        for c in categories:
            if c in self.CATEGORIES:
                cat = self.CATEGORIES[c]
                names.append(f"{cat['emoji']} {cat['name']}")

        text = "✅ *¡Guardado!*\n\n"
        text += "Te enviaré de:\n"
        for name in names:
            text += f"• {name}\n"

        await update.message.reply_text(text, parse_mode="Markdown")
        return "Suscripción guardada"

    async def send_message(self, chat_id: str, message: str) -> bool:
        """Envía mensaje."""

        if not self.app:
            logger.warning(f"Telegram no configurado. Mensaje: {message[:50]}...")
            return False

        try:
            await self.app.bot.send_message(
                chat_id=chat_id, text=message, parse_mode="Markdown"
            )
            logger.info(f"Telegram mensaje enviado a {chat_id}")
            return True
        except Exception as e:
            logger.error(f"Error enviando Telegram: {e}")
            return False

    async def send_daily_summary(self, chat_id: str, news: list[dict]) -> bool:
        """Envía el resumen diario."""

        message = self._format_summary(news)
        return await self.send_message(chat_id, message)

    def _format_summary(self, news: list[dict]) -> str:
        """Formatea el resumen para Telegram."""

        text = "📰 *Resumen de Hoy* 🇧🇴\n\n"

        for i, article in enumerate(news[:10], 1):
            text += f"{i}. *{article.get('title', '')}*\n"
            text += f"   {article.get('summary', '')}\n"
            if article.get("fact"):
                text += f"   📌 {article.get('fact')}\n"
            text += "\n"

        text += "---\n"
        text += "📍 /preferencias | /cancelar"

        return text
