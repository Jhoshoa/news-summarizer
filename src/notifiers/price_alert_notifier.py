from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any

from loguru import logger

from src.db.price_alerts import PriceAlertRepository

# Solo compra/venta P2P -- son los que le importan a un usuario decidiendo
# si comprar o vender USDT ahora mismo. El oficial del BCB no se trackea
# aca: cambia con poca frecuencia y no es el precio al que se opera.
TRACKED_INDICATORS = {
    "binance_p2p_usdt_bob_buy": "Binance P2P compra",
    "binance_p2p_usdt_bob_sell": "Binance P2P venta",
}

# Orden y etiquetas para el comando /precio (BCB primero, luego P2P).
PRICE_DISPLAY_ORDER = [
    ("bcb_tipo_de_cambio_oficial", "Dolar oficial BCB"),
    ("binance_p2p_usdt_bob_buy", "Binance P2P compra"),
    ("binance_p2p_usdt_bob_sell", "Binance P2P venta"),
]


def _format_ts(ts: Any) -> str | None:
    """Fecha y hora (hora de Bolivia) para mostrar en el aviso. None si no
    hay timestamp (p.ej. referencia previa a la migracion 023)."""

    if ts is None:
        return None
    return ts.strftime("%d/%m/%Y %H:%M")


class PriceAlertNotifier:
    """Avisa por Telegram cuando compra o venta P2P se mueve mas de un
    umbral desde la ultima alerta (no desde la corrida anterior, y sin
    resetear por dia -- ver PriceAlertState/PriceAlertRepository para el
    razonamiento completo).

    Bot separado del bot principal de EcoBrief a proposito: distinto
    proposito, distinta audiencia, no se quiere mezclar alertas de precio
    con las suscripciones de noticias. Es abierto, como el bot principal:
    cualquiera que le escriba puede registrarse (guardamos su chat_id en
    price_alert_subscribers) y recibir las alertas. /start registra, /baja
    des-registra y /precio responde los precios actuales al instante.

    Recepcion: corre un long-polling en background (a diferencia del bot
    principal, que usa webhook): no necesita URL publica ni secret token.
    """

    def __init__(
        self,
        settings: Any,
        repository: PriceAlertRepository | None,
        session_maker: Any | None = None,
    ):
        self.settings = settings
        self.repository = repository
        self.session_maker = session_maker
        self.bot = None
        self.subscriber_repo = None
        self._poll_task: asyncio.Task | None = None
        self._stopped = False

        token = getattr(settings, "price_alert_bot_token", None)
        if token:
            if ":" not in token:
                # Un token de BotFather siempre es "<bot_id>:<hash>". Sin el
                # prefijo numerico no es un token real y cada llamada a
                # Telegram devuelve 404 "Not Found" -- mejor deshabilitar ya
                # que reintentar en el polling no va a arreglar nada.
                logger.warning(
                    "Price alert notifier: PRICE_ALERT_BOT_TOKEN no tiene el formato "
                    "<bot_id>:<hash> de BotFather, notifier deshabilitado"
                )
            else:
                try:
                    from telegram import Bot

                    self.bot = Bot(token=token)
                    logger.info("Price alert notifier inicializado")
                except ImportError:
                    logger.warning("python-telegram-bot no esta instalado")
        else:
            logger.info("Price alert notifier inicializado sin token (deshabilitado)")

        if session_maker:
            from src.db.price_alert_subscribers import PriceAlertSubscriberRepository

            self.subscriber_repo = PriceAlertSubscriberRepository(session_maker)

    @property
    def enabled(self) -> bool:
        # Las alertas necesitan DB: la referencia (price_alert_state) y la
        # lista de suscriptores (price_alert_subscribers).
        return bool(self.bot and self.repository and self.session_maker and self.subscriber_repo)

    async def start_polling(self) -> None:
        """Lanza el long-polling de mensajes entrantes en background. No
        falla el arranque: sin token no hace nada, y si el loop muere solo se
        loguea (las alertas salientes siguen funcionando)."""

        if not self.bot:
            return
        if self._poll_task and not self._poll_task.done():
            return
        if not (self.session_maker and self.subscriber_repo):
            logger.warning(
                "Price alert notifier: DB no disponible, el bot no podra "
                "registrar suscriptores ni responder /precio"
            )
        self._stopped = False
        if not await self._validate_bot():
            logger.error(
                "Price alert notifier: bot inaccesible, polling NO iniciado. "
                "Revisa PRICE_ALERT_BOT_TOKEN (debe ser el HTTP API token de "
                "@BotFather, formato <bot_id>:<hash>)"
            )
            self.bot = None
            return
        await self._set_commands()
        self._poll_task = asyncio.create_task(self._poll_loop())
        logger.info("Price alert notifier: polling de mensajes iniciado")

    async def _validate_bot(self) -> bool:
        """Verifica que el token sea de un bot real antes de arrancar el
        polling. Un token invalido o revocado nunca va a funcionar por mas
        que se reintente, asi que falla rapido (una sola llamada) en vez de
        entrar a un loop que reintenta para siempre. No propaga excepciones:
        cualquier fallo aca deshabilita el notifier."""

        try:
            assert self.bot is not None
            me = await self.bot.get_me()
            logger.info(f"Price alert bot validado: @{me.username}")
            return True
        except Exception as e:
            logger.warning(f"Price alert bot no validado (get_me): {e}")
            return False

    async def _set_commands(self) -> None:
        """Publica el menu de comandos del bot (el boton "/" en Telegram), que
        es lo que hace que /precio y /ayuda aparezcan visibles. Best-effort:
        si falla solo se loguea, los comandos siguen funcionando si se
        escriben a mano (y se pueden publicar manualmente con /setcommands
        en BotFather)."""

        try:
            from telegram import BotCommand

            await self.bot.set_my_commands(
                [
                    BotCommand("start", "Suscribirse a las alertas de precio"),
                    BotCommand("precio", "Precio actual del dolar (BCB + P2P)"),
                    BotCommand("baja", "Darse de baja de las alertas"),
                    BotCommand("ayuda", "Ver la ayuda"),
                ]
            )
            logger.info("Price alert notifier: comandos publicados")
        except Exception as e:
            logger.warning(f"No se pudieron publicar los comandos del bot de alertas: {e}")

    async def stop(self) -> None:
        self._stopped = True
        task = self._poll_task
        if task and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        self._poll_task = None

    def _is_fatal_error(self, exc: Exception) -> bool:
        """True si reintentar no tiene sentido: token invalido/revocado/no
        autorizado o conflicto de polling (dos consumidores del mismo token).
        False para transitorios (timeout, red, 5xx) que si vale la pena
        reintentar con backoff."""

        try:
            from telegram.error import Conflict, Forbidden, InvalidToken
        except ImportError:  # pragma: no cover - python-telegram-bot requerido
            return False

        return isinstance(exc, (InvalidToken, Forbidden, Conflict))

    async def _poll_loop(self) -> None:
        offset: int | None = None
        backoff = 1.0
        while not self._stopped:
            try:
                updates = await self.bot.get_updates(
                    offset=offset,
                    timeout=25,
                    allowed_updates=["message"],
                )
                backoff = 1.0
                for update in updates:
                    update_id = getattr(update, "update_id", None)
                    if update_id is not None:
                        offset = int(update_id) + 1
                    try:
                        await self._process_update(update)
                    except Exception as e:
                        logger.error(f"Error procesando update del bot de alertas: {e}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self._is_fatal_error(e):
                    # Token invalido/revocado o conflicto de polling: reintentar
                    # para siempre solo llena Sentry de "Not Found". Se detiene
                    # el loop y se deshabilita el notifier (log claro y fin).
                    logger.error(
                        f"Error fatal en polling del bot de alertas ({e}), "
                        "polling detenido. Revisa PRICE_ALERT_BOT_TOKEN en "
                        "@BotFather: debe ser el HTTP API token completo"
                    )
                    self.bot = None
                    return
                logger.error(f"Error en polling del bot de alertas: {e}")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60.0)

    async def _process_update(self, update) -> None:
        message = getattr(update, "message", None)
        if message is None:
            return
        text = (getattr(message, "text", None) or "").strip()
        if not text:
            return
        from_user = getattr(message, "from_user", None)
        if from_user and getattr(from_user, "is_bot", False):
            return
        chat = getattr(message, "chat", None)
        chat_id = getattr(chat, "id", None)
        if chat_id is None:
            return
        await self.handle_message(str(chat_id), text)

    async def handle_message(self, chat_id: str, text: str) -> None:
        """Responde a cualquier persona que le escriba al bot: /start lo
        registra en las alertas, /precio le da los precios actuales y /baja
        lo des-registra. No propaga excepciones (el polling no debe morir por
        un mensaje con problemas)."""

        if not self.bot:
            return

        try:
            reply = await self._build_reply(chat_id, text)
        except Exception as e:
            logger.error(f"Error armando respuesta para {chat_id}: {e}")
            return

        try:
            await self.bot.send_message(chat_id=chat_id, text=reply, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Error respondiendo en el bot de alertas: {e}")

    async def _build_reply(self, chat_id: str, text: str) -> str:
        normalized = (text or "").strip().lower()

        if normalized == "/start" or normalized.startswith("/start "):
            return await self._start_text(chat_id)
        if normalized in ("/precio", "/precioactual", "/cotizacion", "/cotizaciones", "/dolar"):
            return await self._price_text()
        if normalized in ("/baja", "/cancelar", "/desuscribir", "/unsubscribe"):
            return await self._baja_text(chat_id)
        return self._help_text()

    async def _start_text(self, chat_id: str) -> str:
        subscribed_msg = ""
        if self.subscriber_repo:
            await self.subscriber_repo.add(chat_id)
            subscribed_msg = "Estas suscripto a las alertas de precio.\n"

        threshold = getattr(self.settings, "price_alert_threshold_percent", 1.0)
        text = "*Alertas de precio - dolar en Bolivia*\n\n"
        text += subscribed_msg
        text += "Te aviso cuando el dolar compra/venta P2P (Binance) "
        text += f"se mueve mas de {threshold:g}% desde la ultima alerta.\n\n"
        text += "Comandos:\n"
        text += "/precio - Precios actuales (BCB oficial + P2P)\n"
        text += "/baja - Darte de baja de las alertas\n"
        text += "/ayuda - Ver esta ayuda"
        return text

    def _help_text(self) -> str:
        text = "*Comandos*\n\n"
        text += "/start - Suscribirse a las alertas de precio\n"
        text += "/precio - Precios actuales del dolar\n"
        text += "/baja - Darse de baja\n"
        text += "/ayuda - Ver esta ayuda\n\n"
        text += "Las alertas llegan solas cuando el dolar P2P se mueve mas del umbral de alerta."
        return text

    async def _baja_text(self, chat_id: str) -> str:
        if self.subscriber_repo:
            await self.subscriber_repo.remove(chat_id)
            return "Ya no recibiras alertas de precio. Escribi /start cuando quieras volver."
        return "Me quedo sin acceso a la base de datos, proba mas tarde."

    async def _price_text(self) -> str:
        if not self.session_maker:
            return "La base de datos no esta disponible en este momento."

        from src.db import EconomicIndicatorRepository

        try:
            latest = await EconomicIndicatorRepository(self.session_maker).get_latest_values()
        except Exception as e:
            logger.error(f"Error leyendo precios para /precio: {e}")
            return "No se pudieron leer los precios en este momento."

        by_code = {item.get("indicator_code"): item for item in latest}
        lines = ["*Precio actual del dolar (Bolivia)*"]
        found_any = False
        for code, label in PRICE_DISPLAY_ORDER:
            item = by_code.get(code)
            value = item.get("value") if item else None
            if value is None:
                continue
            found_any = True
            lines.append(f"{label}: Bs {value:.2f}")

        if not found_any:
            return "Todavia no hay precios guardados. El proximo refresh (cada pocos minutos) los carga."

        timestamps = [item["collected_at"] for item in by_code.values() if item.get("collected_at")]
        if timestamps:
            newest = max(timestamps)
            lines.append("")
            lines.append(f"Actualizado: {newest.strftime('%d/%m/%Y %H:%M')} hora de Bolivia")

        return "\n".join(lines)

    async def check_and_notify(self, indicators: list[dict[str, Any]]) -> None:
        """Revisa cada indicador trackeado contra su referencia guardada y
        avisa a todos los suscriptores si se movio mas del umbral. No
        propaga excepciones: un fallo aca no debe tumbar el refresh de
        indicadores que lo llama."""

        if not self.enabled:
            return

        by_code = {item.get("indicator_code"): item for item in indicators}
        threshold_ratio = Decimal(str(self.settings.price_alert_threshold_percent)) / 100
        chat_ids = await self.subscriber_repo.list_chat_ids()
        if not chat_ids:
            return

        for code, label in TRACKED_INDICATORS.items():
            item = by_code.get(code)
            if not item or item.get("value") is None:
                continue

            try:
                await self._check_one(
                    code,
                    label,
                    Decimal(str(item["value"])),
                    item.get("collected_at"),
                    threshold_ratio,
                    chat_ids,
                )
            except Exception as e:
                logger.error(f"Error revisando alerta de precio para {code}: {e}")

    async def _check_one(
        self,
        code: str,
        label: str,
        value: Decimal,
        collected_at: Any,
        threshold_ratio: Decimal,
        chat_ids: list[str],
    ) -> None:
        reference = await self.repository.get_reference_with_time(code)

        if reference is None:
            # Primera vez que vemos este indicador: se establece la
            # referencia inicial sin avisar (no hay "movimiento" que reportar
            # todavia, solo un punto de partida).
            await self.repository.set_reference(code, value, collected_at)
            return

        reference_value, reference_collected_at = reference
        if reference_value == 0:
            return

        change_ratio = (value - reference_value) / reference_value
        if abs(change_ratio) < threshold_ratio:
            return

        all_sent = await self._send_alerts(
            label,
            reference_value,
            reference_collected_at,
            value,
            collected_at,
            change_ratio,
            chat_ids,
        )
        if all_sent:
            # Se "rearma" solo si el aviso salio de verdad a todos -- si un
            # chat fallo (bot caido, chat invalido), la proxima corrida vuelve
            # a intentar con el mismo movimiento acumulado en vez de perder el
            # evento en silencio (quienes ya lo recibieron veran un duplicado,
            # menos grave que perder un movimiento de precio).
            await self.repository.set_reference(code, value, collected_at)

    async def _send_alerts(
        self,
        label: str,
        reference: Decimal,
        reference_time: Any,
        value: Decimal,
        value_time: Any,
        change_ratio: Decimal,
        chat_ids: list[str],
    ) -> bool:
        direction = "subio" if change_ratio > 0 else "bajo"
        percent = abs(change_ratio) * 100

        delta = value - reference
        delta_sign = "+" if delta > 0 else "-"
        change_absolute = f"{delta_sign}Bs {abs(delta):.2f}"

        ref_time = _format_ts(reference_time)
        val_time = _format_ts(value_time)

        def _with_time(v: Decimal, ts: str | None) -> str:
            text = f"Bs {v:.2f}"
            return f"{text} - {ts}" if ts else text

        message = (
            f"*Alerta de precio*\n\n"
            f"{label} {direction} {percent:.2f}% ({change_absolute})\n\n"
            f"Referencia (ultima alerta): {_with_time(reference, ref_time)}\n"
            f"Precio actual: {_with_time(value, val_time)}\n\n"
            f"Se compara contra la ultima alerta enviada, no contra el dia anterior."
        )

        all_sent = True
        for chat_id in chat_ids:
            try:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode="Markdown",
                )
                logger.info(
                    f"Alerta de precio enviada a {chat_id}: {label} {direction} {percent:.2f}%"
                )
            except Exception as e:
                logger.error(f"Error enviando alerta de precio a {chat_id}: {e}")
                all_sent = False
                if self._is_fatal_error(e):
                    # Token invalido/revocado: no tiene sentido seguir
                    # pinging a cada chat, y no se debe rearmar la referencia
                    # (el proximo refresh reintentara). Se deshabilita el
                    # notifier de una.
                    logger.error(
                        "Token del bot de alertas invalido o no autorizado, "
                        "notifier deshabilitado. Revisa PRICE_ALERT_BOT_TOKEN"
                    )
                    self.bot = None
                    break
        return all_sent
