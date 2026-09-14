import re
from contextlib import suppress
from typing import Any

import sentry_sdk
from loguru import logger

from src.db.repository import DEFAULT_CATEGORIES

_MARKDOWN_V1_SPECIAL_CHARS = re.compile(r"([_*`\[])")
_MAX_CAPTION_LENGTH = 1000  # Telegram limita el caption de una foto a 1024


def _escape_markdown(value: str) -> str:
    """Escapa los caracteres especiales del modo Markdown (v1) de Telegram
    para poder interpolar texto dinamico (titulos de noticias reales) sin
    que un `_`/`*`/`` ` ``/`[` suelto rompa el parseo del mensaje."""

    return _MARKDOWN_V1_SPECIAL_CHARS.sub(r"\\\1", value)


class TelegramHandler:
    """Maneja el bot de Telegram.

    Envio: usa un `telegram.Bot` directo (no un `Application` completo), que
    no necesita inicializacion async previa para llamadas simples como
    send_message. Recepcion: `process_update` recibe el payload crudo del
    webhook (`/webhook/telegram` en main.py) y lo despacha a `handle_message`
    sin pasar por el sistema de handlers de `Application` — mas simple y
    evita correr un loop de polling dentro de FastAPI.
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
        self.bot = None
        self._username: str | None = None

        if settings and settings.telegram_bot_token:
            try:
                from telegram import Bot

                self.bot = Bot(token=settings.telegram_bot_token)
                logger.info("Telegram handler inicializado")
            except ImportError:
                logger.warning("python-telegram-bot no esta instalado")
        else:
            logger.info("Telegram handler inicializado sin token (modo desarrollo)")

    async def get_username(self) -> str | None:
        """@username del bot, para armar el deep link `t.me/<username>?start=...`.

        Se cachea tras la primera consulta -- no cambia en caliente y evita
        pegarle a la API de Telegram en cada request que arma un link.
        """

        if not self.bot:
            return None
        if self._username is None:
            try:
                me = await self.bot.get_me()
                self._username = me.username
            except Exception as e:
                logger.warning(f"No se pudo obtener el username del bot de Telegram: {e}")
                return None
        return self._username

    async def process_update(self, payload: dict[str, Any]) -> None:
        """Procesa un update entrante recibido por webhook (Fase distribucion).

        No propaga excepciones: un update malformado o un error de Telegram
        no debe tumbar el endpoint del webhook (Telegram reintentaria de
        todos modos si respondemos error).
        """

        if not self.bot:
            logger.warning("Telegram update recibido pero el bot no esta configurado")
            return

        try:
            from telegram import Update

            update = Update.de_json(payload, self.bot)
            await self.handle_message(update, context=None)
        except Exception as e:
            logger.error(f"Error procesando update de Telegram: {e}")
            sentry_sdk.capture_exception(e)

    async def handle_message(self, update, context) -> str | None:
        """Procesa mensaje entrante."""

        if update.callback_query:
            return await self._handle_callback_selection(update, context)

        if not update.message:
            return None

        raw_text = (update.message.text or "").strip()
        text = raw_text.upper()
        chat_id = str(update.message.chat.id)

        if text == "/START" or text.startswith("/START "):
            # El deep link `t.me/<bot>?start=<token>` llega como "/start <token>";
            # el token es case-sensitive (base64 urlsafe), asi que se extrae de
            # raw_text, nunca de la version en mayusculas usada para comandos.
            token = raw_text[len("/start") :].strip()
            if token:
                confirmed = await self._handle_start_with_token(update, chat_id, token)
                if confirmed:
                    return confirmed
                with suppress(Exception):
                    await update.message.reply_text(
                        "El codigo de suscripcion vencio o ya se uso. Elegi tus categorias abajo:"
                    )
            return await self._handle_start(update, context)

        handlers = {
            "/AYUDA": self._handle_help,
            "/HELP": self._handle_help,
            "HOLA": self._handle_start,
            "INICIO": self._handle_start,
            "/PREFERENCIAS": self._handle_preferences,
            "/PREFERENCIA": self._handle_preferences,
            "/CANCELAR": self._handle_cancel,
            "/BAJA": self._handle_cancel,
            "/NOTICIAS": self._handle_on_demand_news,
            "/HOY": self._handle_on_demand_news,
        }

        handler = handlers.get(text)
        if handler:
            return await handler(update, context)

        return await self._handle_selection(update, context, chat_id, text)

    async def _handle_start_with_token(self, update, chat_id: str, token: str) -> str | None:
        """Consume el token del deep link generado desde el formulario web
        (categorias/frecuencia/hora ya elegidas ahi) y guarda la suscripcion
        completa de una. None si el token no existe/ya vencio/ya se uso --
        el caller cae al flujo normal de botones en ese caso.
        """

        if not self.db or not getattr(self.db, "session_maker", None):
            return None

        from src.db.telegram_links import TelegramLinkRepository

        repo = TelegramLinkRepository(self.db.session_maker)
        preferences = await repo.consume_link(token)
        if not preferences:
            return None

        categories = set(preferences["categories"]) or {"general"}
        await self.db.save_subscription(
            telegram_id=chat_id,
            channel="telegram",
            categories=categories,
            frequency=preferences["frequency"],
            preferred_hour=preferences["preferred_hour"],
            timezone=preferences["timezone"],
            consent_accepted=True,
        )

        category_names = ", ".join(sorted(categories))
        text = "*Preferencias guardadas en EcoBrief Bolivia*\n\n"
        text += f"Categorias: {category_names}\n"
        text += f"Frecuencia: {preferences['frequency']}\n"
        text += f"Hora: {preferences['preferred_hour']:02d}:00 (hora Bolivia)\n\n"
        text += "Escribi /noticias cuando quieras tu brief al toque, sin esperar el envio diario.\n"
        text += "Podes cambiar tus categorias cuando quieras con /preferencias."

        await update.message.reply_text(text, parse_mode="Markdown")
        return "Suscripcion guardada desde la web"

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
        text += "/noticias - Pedir tu brief ahora mismo\n"
        text += "/preferencias - Cambiar categorias\n"
        text += "/cancelar - Darse de baja\n"
        text += "/ayuda - Ver ayuda"

        await update.message.reply_text(text, parse_mode="Markdown")
        return text

    async def _handle_on_demand_news(self, update, context) -> str:
        """Comando /noticias (alias /hoy): entrega el brief actual a demanda,
        sin esperar el envio programado. Reusa las categorias que ya eligio
        al suscribirse -- no vuelve a preguntar nada."""

        chat_id = str(update.message.chat.id)

        if not self.db:
            await update.message.reply_text("El servicio no esta disponible en este momento.")
            return "DB no disponible"

        subscription = await self.db.get_subscriber_by_telegram_id(chat_id)
        if not subscription:
            await update.message.reply_text(
                "Todavia no estas suscripto. Usa /start para elegir tus categorias."
            )
            return "No suscripto"

        categories = subscription.get("categories") or ["general"]
        items = await self.db.get_preference_preview(categories, limit=8)

        if not items:
            await update.message.reply_text(
                "No hay noticias nuevas en tus categorias por ahora. Proba mas tarde con /noticias."
            )
            return "Sin noticias nuevas"

        await update.message.reply_text(
            f"*Tu brief de EcoBrief Bolivia* ({len(items)} noticias)", parse_mode="Markdown"
        )

        indexed_items = list(enumerate(items, start=1))
        with_image = [(i, item) for i, item in indexed_items if item.get("image_url")]
        without_image = [(i, item) for i, item in indexed_items if not item.get("image_url")]

        group_sent = False
        if with_image:
            from telegram import InputMediaPhoto

            # sendMediaGroup es todo-o-nada: si Telegram no puede bajar una
            # sola de las imagenes, falla el grupo entero (no solo esa foto).
            # Por eso el fallback de abajo no distingue "parcial" -- si esto
            # tira, se manda todo item por item como antes de esta funcion.
            media = [
                InputMediaPhoto(
                    media=item["image_url"],
                    caption=self._format_news_card(item, i),
                    parse_mode="Markdown",
                )
                for i, item in with_image
            ]
            try:
                await update.message.reply_media_group(media=media)
                group_sent = True
            except Exception as e:
                logger.warning(f"No se pudo mandar el album de Telegram a {chat_id}: {e}")

        photos_sent = len(with_image) if group_sent else 0
        fallback_items = without_image if group_sent else indexed_items

        for index, item in fallback_items:
            card = self._format_news_card(item, index)
            image_url = item.get("image_url")
            sent_as_photo = False

            if image_url:
                try:
                    await update.message.reply_photo(
                        photo=image_url, caption=card, parse_mode="Markdown"
                    )
                    sent_as_photo = True
                except Exception as e:
                    logger.warning(
                        f"No se pudo mandar la foto de '{item.get('title')}' a {chat_id}: {e}"
                    )

            if sent_as_photo:
                photos_sent += 1
            else:
                # Sin imagen, o Telegram no pudo bajarla (link roto, timeout,
                # formato no soportado): la misma card, como texto.
                await update.message.reply_text(card, parse_mode="Markdown")

        await update.message.reply_text("/preferencias para cambiar categorias | /cancelar para darte de baja")
        logger.info(
            f"Brief a demanda enviado a {chat_id}: {photos_sent}/{len(items)} con foto "
            f"(grupo={'si' if group_sent else 'no'})"
        )
        return "Brief enviado a demanda"

    def _format_news_card(self, item: dict, index: int) -> str:
        """Arma el texto de una noticia -- se usa igual como caption de una
        foto o como mensaje de texto solo, para que el fallback sin imagen
        se vea igual de prolijo, no como un texto plano de relleno."""

        category_label = DEFAULT_CATEGORIES.get(
            str(item.get("category") or ""), str(item.get("category") or "").capitalize()
        )
        title = _escape_markdown(str(item.get("title") or ""))
        summary = str(item.get("summary") or "")
        if len(summary) > 280:
            summary = summary[:277].rstrip() + "..."
        fact = item.get("fact")

        lines = [f"{index}. *{title}*", f"_{category_label}_"]
        if summary:
            lines.append("")
            lines.append(_escape_markdown(summary))
        if fact:
            lines.append("")
            lines.append(f"Dato: {_escape_markdown(str(fact))}")

        body = "\n".join(lines)
        # Deja margen para el link "leer completo" que se agrega abajo sin
        # escapar (es una URL real, no texto de usuario) -- truncar el bloque
        # ANTES de agregarlo evita cortar el link a la mitad, lo que lo
        # dejaria roto/no clickeable.
        if len(body) > _MAX_CAPTION_LENGTH - 100:
            body = body[: _MAX_CAPTION_LENGTH - 103].rstrip() + "..."

        article_id = item.get("article_id")
        site_base_url = getattr(self.settings, "site_base_url", None) if self.settings else None
        if article_id and site_base_url:
            link = f"{site_base_url.rstrip('/')}/article/{article_id}"
            body += f"\n\n[Leer completo]({link})"

        return body

    async def _handle_callback_selection(self, update, context) -> str | None:
        """Procesa el tap en los botones inline de categorias (callback_query).

        `_show_categories` los genera con callback_data "cat_1".."cat_5" y
        "cat_todas"; a diferencia de un mensaje de texto, Telegram requiere
        `answer()` para quitar el spinner de carga del boton.
        """

        query = update.callback_query
        if not query or not query.message:
            return None

        with suppress(Exception):
            await query.answer()

        data = (query.data or "").strip()
        if data == "cat_todas":
            selected_keys = set(self.CATEGORIES.keys())
        else:
            match = re.fullmatch(r"cat_(\d)", data)
            if not match or match.group(1) not in self.CATEGORIES:
                return None
            selected_keys = {match.group(1)}

        chat_id = str(query.message.chat.id)
        return await self._save_selection(chat_id, selected_keys, query.message)

    async def _handle_selection(self, update, context, chat_id: str, text: str) -> str:
        """Procesa seleccion de categorias enviada como texto (ej. '1 3')."""

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

        return await self._save_selection(chat_id, selected_keys, update.message)

    async def _save_selection(self, chat_id: str, selected_keys: set[str], reply_target) -> str:
        """Guarda la suscripcion y confirma, usado por texto y por botones."""

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
        text += "\nEscribi /noticias cuando quieras tu brief al toque, sin esperar el envio diario."

        await reply_target.reply_text(text, parse_mode="Markdown")
        return "Suscripcion guardada"

    async def send_message(self, chat_id: str, message: str) -> bool:
        """Envia mensaje."""

        if not self.bot:
            logger.warning(f"Telegram no configurado. Mensaje: {message[:50]}...")
            return False

        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="Markdown",
            )
            logger.info(f"Telegram mensaje enviado a {chat_id}")
            return True
        except Exception as e:
            logger.error(f"Error enviando Telegram: {e}")
            sentry_sdk.capture_exception(e)
            return False

