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


class PriceAlertNotifier:
    """Avisa por Telegram cuando compra o venta P2P se mueve mas de un
    umbral desde la ultima alerta (no desde la corrida anterior, y sin
    resetear por dia -- ver PriceAlertState/PriceAlertRepository para el
    razonamiento completo).

    A diferencia del bot principal de EcoBrief (que usa webhook), este bot
    corre un long-polling en background: no tiene URL publica, es personal y
    de bajo volumen. Responde /start (bienvenida) y /precio (precios
    actuales BCB + P2P) solo al chat configurado en PRICE_ALERT_CHAT_ID.

    Bot separado del bot principal de EcoBrief a proposito: distinto
    proposito, distinta audiencia, no se quiere mezclar alertas de precio
    con las suscripciones de noticias.
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
        self._poll_task: asyncio.Task | None = None
        self._stopped = False

        token = getattr(settings, "price_alert_bot_token", None)
        if token:
            try:
                from telegram import Bot

                self.bot = Bot(token=token)
                logger.info("Price alert notifier inicializado")
            except ImportError:
                logger.warning("python-telegram-bot no esta instalado")
        else:
            logger.info("Price alert notifier inicializado sin token (deshabilitado)")

    @property
    def enabled(self) -> bool:
        return bool(
            self.bot
            and self.repository
            and getattr(self.settings, "price_alert_chat_id", None)
        )

    async def start_polling(self) -> None:
        """Lanza el long-polling de mensajes entrantes en background. No
        falla el arranque: sin token no hace nada, y si el loop muere solo se
        loguea (las alertas salientes siguen funcionando)."""

        if not self.bot:
            return
        if self._poll_task and not self._poll_task.done():
            return
        self._stopped = False
        self._poll_task = asyncio.create_task(self._poll_loop())
        logger.info("Price alert notifier: polling de mensajes iniciado")

    async def stop(self) -> None:
        self._stopped = True
        task = self._poll_task
        if task and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        self._poll_task = None

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
        """Responde a un mensaje entrante, solo si viene del chat configurado
        en PRICE_ALERT_CHAT_ID. Un mensaje de cualquier otro chat se ignora:
        este bot es personal, no publico."""

        expected_chat = getattr(self.settings, "price_alert_chat_id", None)
        if not self.bot or not expected_chat or str(chat_id) != str(expected_chat):
            return

        reply = await self._build_reply(text)
        try:
            await self.bot.send_message(chat_id=chat_id, text=reply, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Error respondiendo en el bot de alertas: {e}")

    async def _build_reply(self, text: str) -> str:
        normalized = (text or "").strip().lower()

        if normalized == "/start" or normalized.startswith("/start "):
            return self._welcome_text()
        if normalized in ("/precio", "/precioactual", "/cotizacion", "/cotizaciones", "/dolar"):
            return await self._price_text()
        return self._help_text()

    def _welcome_text(self) -> str:
        threshold = getattr(self.settings, "price_alert_threshold_percent", 1.0)
        text = "*Alertas de precio - dolar en Bolivia*\n\n"
        text += "Te aviso por Telegram cuando el dolar compra/venta P2P (Binance) "
        text += f"se mueve mas de {threshold:g}% desde la ultima alerta.\n\n"
        text += "Comandos:\n"
        text += "/precio - Precios actuales (BCB oficial + P2P)\n"
        text += "/ayuda - Ver esta ayuda"
        return text

    def _help_text(self) -> str:
        text = "*Comandos*\n\n"
        text += "/precio - Precios actuales del dolar\n"
        text += "/ayuda - Ver esta ayuda\n\n"
        text += "Las alertas llegan solas cuando el dolar P2P se mueve mas del umbral de alerta."
        return text

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

        timestamps = [
            item["collected_at"]
            for item in by_code.values()
            if item.get("collected_at")
        ]
        if timestamps:
            newest = max(timestamps)
            lines.append("")
            lines.append(f"Actualizado: {newest.strftime('%d/%m/%Y %H:%M')} hora de Bolivia")

        return "\n".join(lines)

    async def check_and_notify(self, indicators: list[dict[str, Any]]) -> None:
        """Revisa cada indicador trackeado contra su referencia guardada y
        avisa si se movio mas del umbral. No propaga excepciones: un fallo
        aca no debe tumbar el refresh de indicadores que lo llama."""

        if not self.enabled:
            return

        by_code = {item.get("indicator_code"): item for item in indicators}
        threshold_ratio = Decimal(str(self.settings.price_alert_threshold_percent)) / 100

        for code, label in TRACKED_INDICATORS.items():
            item = by_code.get(code)
            if not item or item.get("value") is None:
                continue

            try:
                await self._check_one(code, label, Decimal(str(item["value"])), threshold_ratio)
            except Exception as e:
                logger.error(f"Error revisando alerta de precio para {code}: {e}")

    async def _check_one(
        self,
        code: str,
        label: str,
        value: Decimal,
        threshold_ratio: Decimal,
    ) -> None:
        reference = await self.repository.get_reference(code)

        if reference is None:
            # Primera vez que vemos este indicador: se establece la
            # referencia inicial sin avisar (no hay "movimiento" que reportar
            # todavia, solo un punto de partida).
            await self.repository.set_reference(code, value)
            return

        if reference == 0:
            return

        change_ratio = (value - reference) / reference
        if abs(change_ratio) < threshold_ratio:
            return

        sent = await self._send_alert(label, reference, value, change_ratio)
        if sent:
            # Se "rearma" solo si el aviso salio de verdad -- si Telegram
            # fallo (bot caido, chat_id invalido), la proxima corrida vuelve
            # a intentar con el mismo movimiento acumulado en vez de perder
            # el evento en silencio.
            await self.repository.set_reference(code, value)

    async def _send_alert(
        self,
        label: str,
        reference: Decimal,
        value: Decimal,
        change_ratio: Decimal,
    ) -> bool:
        direction = "subio" if change_ratio > 0 else "bajo"
        percent = abs(change_ratio) * 100

        message = (
            f"*Alerta de precio*\n\n"
            f"{label} {direction} {percent:.2f}%\n"
            f"Bs {reference:.2f} -> Bs {value:.2f}"
        )

        try:
            await self.bot.send_message(
                chat_id=self.settings.price_alert_chat_id,
                text=message,
                parse_mode="Markdown",
            )
            logger.info(f"Alerta de precio enviada: {label} {direction} {percent:.2f}%")
            return True
        except Exception as e:
            logger.error(f"Error enviando alerta de precio: {e}")
            return False
