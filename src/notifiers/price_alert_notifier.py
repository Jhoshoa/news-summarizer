from __future__ import annotations

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


class PriceAlertNotifier:
    """Avisa por Telegram cuando compra o venta P2P se mueve mas de un
    umbral desde la ultima alerta (no desde la corrida anterior, y sin
    resetear por dia -- ver PriceAlertState/PriceAlertRepository para el
    razonamiento completo).

    Bot separado del bot principal de EcoBrief a proposito: distinto
    proposito, distinta audiencia, no se quiere mezclar alertas de precio
    con las suscripciones de noticias.
    """

    def __init__(
        self,
        settings: Any,
        repository: PriceAlertRepository | None,
    ):
        self.settings = settings
        self.repository = repository
        self.bot = None

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
