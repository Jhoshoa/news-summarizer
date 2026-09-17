from __future__ import annotations

import re
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from bs4 import BeautifulSoup
from loguru import logger

TZ_BOLIVIA = ZoneInfo("America/La_Paz")


@dataclass
class EconomicIndicator:
    source: str
    indicator_code: str
    indicator_name: str
    indicator_group: str
    value: Decimal
    unit: str | None = None
    currency: str | None = None
    asset: str | None = None
    side: str | None = None
    observed_at: date | None = None
    collected_at: datetime | None = None
    snapshot_key: str | None = None
    raw_payload: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "indicator_code": self.indicator_code,
            "indicator_name": self.indicator_name,
            "indicator_group": self.indicator_group,
            "value": self.value,
            "unit": self.unit,
            "currency": self.currency,
            "asset": self.asset,
            "side": self.side,
            "observed_at": self.observed_at,
            "collected_at": self.collected_at,
            "snapshot_key": self.snapshot_key,
            "raw_payload": self.raw_payload or {},
        }


class EconomicIndicatorCollector:
    BCB_URL = "https://www.bcb.gob.bo/"
    BCB_OFFICIAL_USD_URL = "https://www.bcb.gob.bo/tco_reporte_ultima_cotizacion.php"
    BINANCE_P2P_URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    # Un anunciante con pocas ordenes en el mes y/o mala tasa de completado
    # puede publicar un precio fuera de mercado (carnada, error, o un
    # anuncio que nunca llega a operarse) y desaparecer poco despues. Caso
    # real: un anuncio de venta a Bs 12.03 (vs. ~10.7-10.9 del resto del
    # lote) vino de un anunciante con 4 ordenes en el mes y 36% de tasa de
    # completado -- tomar el maximo/minimo crudo de 20 anuncios sin filtrar
    # por esto produce picos de un solo punto que no reflejan ningun precio
    # real operable.
    MIN_ADVERTISER_ORDER_COUNT = 10
    MIN_ADVERTISER_FINISH_RATE = 0.80

    MONTHS_ES = {
        "enero": 1,
        "febrero": 2,
        "marzo": 3,
        "abril": 4,
        "mayo": 5,
        "junio": 6,
        "julio": 7,
        "agosto": 8,
        "septiembre": 9,
        "setiembre": 9,
        "octubre": 10,
        "noviembre": 11,
        "diciembre": 12,
    }

    def __init__(self, timeout: int = 30, user_agent: str | None = None):
        self.timeout = timeout
        self.user_agent = user_agent or self.USER_AGENT

    async def fetch_all(self) -> list[dict[str, Any]]:
        snapshot_key = str(uuid.uuid4())
        collected_at = datetime.now(TZ_BOLIVIA).replace(tzinfo=None)
        timeout = httpx.Timeout(float(self.timeout), connect=min(10.0, float(self.timeout)))
        headers = {"User-Agent": self.user_agent}

        async with httpx.AsyncClient(
            headers=headers,
            timeout=timeout,
            follow_redirects=True,
        ) as client:
            indicators = []
            indicators.extend(await self.fetch_bcb(client, snapshot_key, collected_at))
            indicators.extend(await self.fetch_binance_p2p(client, snapshot_key, collected_at))

        return [indicator.to_dict() for indicator in indicators]

    async def fetch_bcb(
        self,
        client: httpx.AsyncClient,
        snapshot_key: str | None = None,
        collected_at: datetime | None = None,
    ) -> list[EconomicIndicator]:
        response = await client.get(self.BCB_URL)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        section = soup.select_one('[aria-label="Indicadores clave - BCB"]') or soup.select_one(
            ".bcb-kpi2"
        )
        if not section:
            logger.warning("BCB indicators section was not found")
            return []

        indicators = []
        official_rate = None
        for card in section.select(".bcb-kpi2-card"):
            if card.select_one(".bcb-tco-amount") or self._is_bcb_exchange_rate_card(card):
                official_rate = self._parse_bcb_official_rate_card(
                    card,
                    snapshot_key=snapshot_key,
                    collected_at=collected_at,
                )
                continue
            indicators.extend(
                self._parse_bcb_card(
                    card,
                    snapshot_key=snapshot_key,
                    collected_at=collected_at,
                )
            )

        if official_rate is not None:
            # El home muestra el tipo de cambio oficial vigente directamente
            # (tarjeta .bcb-tco-amount); solo se recurre al reporte aparte
            # (tco_reporte_ultima_cotizacion.php) si esa tarjeta no aparece.
            # Ese reporte es un indicador distinto -- el promedio ponderado de
            # transacciones bancarias reportadas a BCB, que se publica con
            # dias/semanas de rezago -- y usarlo como si fuera el oficial
            # mostraba un valor desactualizado (caso real: home informaba
            # 12,58 vigente para el 5-7 de septiembre 2026 mientras el
            # reporte aun mostraba 11,52 con vigencia del 21 de agosto).
            indicators.append(official_rate)
        else:
            indicators.extend(
                await self._fetch_official_usd_rate(
                    client,
                    snapshot_key=snapshot_key,
                    collected_at=collected_at,
                )
            )

        return indicators

    async def fetch_binance_p2p(
        self,
        client: httpx.AsyncClient,
        snapshot_key: str | None = None,
        collected_at: datetime | None = None,
    ) -> list[EconomicIndicator]:
        headers = {"Content-Type": "application/json", "User-Agent": self.user_agent}
        requests = [
            ("buy", "BUY"),
            ("sell", "SELL"),
        ]
        indicators = []

        for side, trade_type in requests:
            payload = {
                "page": 1,
                "rows": 20,
                "payTypes": [],
                "asset": "USDT",
                "tradeType": trade_type,
                "fiat": "BOB",
                "publisherType": None,
            }
            response = await client.post(self.BINANCE_P2P_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            price, raw_ad, selection = self._best_binance_price(data, trade_type)
            if price is None:
                logger.warning(f"No Binance P2P price found for tradeType={trade_type}")
                continue

            indicators.append(
                EconomicIndicator(
                    source="binance_p2p",
                    indicator_code=f"binance_p2p_usdt_bob_{side}",
                    indicator_name=f"Binance P2P USDT/BOB {side}",
                    indicator_group="p2p_exchange_rate",
                    value=price,
                    unit="BOB per USDT",
                    currency="BOB",
                    asset="USDT",
                    side=side,
                    observed_at=date.today(),
                    collected_at=collected_at or datetime.now(TZ_BOLIVIA).replace(tzinfo=None),
                    snapshot_key=snapshot_key,
                    raw_payload={
                        "trade_type": trade_type,
                        "selection": selection,
                        "request": payload,
                        "advertisement": raw_ad,
                    },
                )
            )

        return indicators

    async def _fetch_official_usd_rate(
        self,
        client: httpx.AsyncClient,
        *,
        snapshot_key: str | None = None,
        collected_at: datetime | None = None,
    ) -> list[EconomicIndicator]:
        try:
            response = await client.get(self.BCB_OFFICIAL_USD_URL)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")
            value_text, observed_at, validity_label = self._parse_official_usd_report(soup)
            value = self._parse_decimal(value_text)
            if value is None:
                logger.warning("Could not parse BCB official USD rate")
                return []
        except Exception:
            logger.exception("Failed to fetch BCB official USD rate")
            return []

        return [
            EconomicIndicator(
                source="bcb",
                indicator_code="bcb_tipo_de_cambio_oficial",
                indicator_name="Dolar oficial",
                indicator_group="Tipo de cambio oficial",
                value=value,
                unit="BOB per USD",
                currency="BOB",
                asset="USD",
                side=None,
                observed_at=observed_at,
                collected_at=collected_at or datetime.now(TZ_BOLIVIA).replace(tzinfo=None),
                snapshot_key=snapshot_key,
                raw_payload={
                    "value_text": value_text,
                    "validity_label": validity_label,
                    "source_url": self.BCB_OFFICIAL_USD_URL,
                },
            )
        ]

    def _parse_bcb_official_rate_card(
        self,
        card,
        *,
        snapshot_key: str | None,
        collected_at: datetime | None,
    ) -> EconomicIndicator | None:
        value_text = self._clean_text(
            card.select_one(".bcb-tco-num") or card.select_one(".bcb-tco-amount")
        )
        value = self._parse_decimal(value_text)
        if value is None:
            return None

        asof_element = card.select_one(".bcb-kpi2-asof")
        observed_label = self._clean_text(asof_element)
        observed_at = self._parse_asof_date(asof_element, observed_label)

        return EconomicIndicator(
            source="bcb",
            indicator_code="bcb_tipo_de_cambio_oficial",
            indicator_name="Dolar oficial",
            indicator_group="Tipo de cambio oficial",
            value=value,
            unit="BOB per USD",
            currency="BOB",
            asset="USD",
            side=None,
            observed_at=observed_at,
            collected_at=collected_at or datetime.now(TZ_BOLIVIA).replace(tzinfo=None),
            snapshot_key=snapshot_key,
            raw_payload={
                "value_text": value_text,
                "validity_label": observed_label,
                "source_url": self.BCB_URL,
            },
        )

    def _parse_asof_date(self, element: Any, fallback_text: str) -> date | None:
        """Fecha de vigencia de una tarjeta BCB.

        Preferimos el atributo `datetime` del `<time>` (ISO, inequivoco) sobre
        parsear el texto en espanol: para rangos "vigente para el sabado 5,
        domingo 6 y lunes 7 de septiembre" el regex de `_parse_spanish_date`
        solo encuentra la ultima fecha por casualidad de formato (es la unica
        seguida de "de <mes>"), y ese acoplamiento se rompe si BCB cambia el
        orden o la redaccion del rango.
        """

        time_tag = element.select_one("time[datetime]") if element is not None else None
        if time_tag is not None:
            try:
                return date.fromisoformat(time_tag["datetime"][:10])
            except (KeyError, ValueError):
                pass

        return self._parse_spanish_date(fallback_text)

    def _is_bcb_exchange_rate_card(self, card) -> bool:
        title = self._clean_text(card.select_one(".bcb-kpi2-name"))
        subtitle = self._clean_text(card.select_one(".bcb-kpi2-sub"))
        text = self._strip_accents(f"{title} {subtitle}".lower())
        return "tipo de cambio" in text and ("dolar" in text or "dollar" in text)

    def _parse_official_usd_report(self, soup: BeautifulSoup) -> tuple[str | None, date | None, str]:
        value_text = self._clean_text(soup.select_one(".tco-public-value"))
        validity_label = self._clean_text(soup.select_one(".tco-public-vigencia"))
        observed_at = self._parse_spanish_date(validity_label)
        if value_text:
            return value_text, observed_at, validity_label

        daily_table = soup.select_one(".tco-daily-table")
        if not daily_table:
            return None, observed_at, validity_label

        latest_date = None
        latest_value = None
        for row in daily_table.select("tbody tr"):
            cells = [self._clean_text(cell) for cell in row.select("td")]
            if len(cells) >= 2:
                latest_date = self._parse_spanish_date(cells[0]) or latest_date
                latest_value = cells[1]

        return latest_value, observed_at or latest_date, validity_label

    def _parse_bcb_card(
        self,
        card,
        *,
        snapshot_key: str | None,
        collected_at: datetime | None,
    ) -> list[EconomicIndicator]:
        group_name = self._clean_text(card.select_one(".bcb-kpi2-name"))
        subtitle = self._clean_text(card.select_one(".bcb-kpi2-sub"))
        asof_element = card.select_one(".bcb-kpi2-asof")
        observed_label = self._clean_text(asof_element)
        observed_at = self._parse_asof_date(asof_element, observed_label)
        indicators = []
        for label, value_text in self._iter_bcb_values(card):
            value = self._parse_decimal(value_text)
            if not group_name or not label or value is None:
                continue
            unit = self._infer_bcb_unit(group_name, f"{subtitle} {label}")
            currency, asset = self._infer_bcb_market(group_name, subtitle, label)

            indicators.append(
                EconomicIndicator(
                    source="bcb",
                    indicator_code=self._slugify(f"bcb {group_name} {label}"),
                    indicator_name=label,
                    indicator_group=group_name,
                    value=value,
                    unit=unit,
                    currency=currency,
                    asset=asset,
                    side=self._normalize_side(label),
                    observed_at=observed_at,
                    collected_at=collected_at or datetime.now(TZ_BOLIVIA).replace(tzinfo=None),
                    snapshot_key=snapshot_key,
                    raw_payload={
                        "group": group_name,
                        "subtitle": subtitle,
                        "observed_label": observed_label,
                        "label": label,
                        "value_text": value_text,
                    },
                )
            )

        return indicators

    def _iter_bcb_values(self, card) -> list[tuple[str, str]]:
        rows = []
        for row in card.select(".bcb-row"):
            rows.append(
                (
                    self._clean_text(row.select_one(".bcb-lbl")),
                    self._clean_text(row.select_one(".bcb-val")),
                )
            )
        if rows:
            return rows

        labels = [self._clean_text(label) for label in card.select(".bcb-lbl")]
        values = [self._clean_text(value) for value in card.select(".bcb-val")]
        return list(zip(labels, values, strict=False))

    def _is_reliable_advertiser(self, item: dict[str, Any]) -> bool:
        """Filtra anunciantes con poco historial o mal record de completado
        -- ver MIN_ADVERTISER_ORDER_COUNT/MIN_ADVERTISER_FINISH_RATE arriba."""

        advertiser = item.get("advertiser") or {}
        order_count = advertiser.get("monthOrderCount")
        finish_rate = advertiser.get("monthFinishRate")

        if order_count is None or finish_rate is None:
            return False
        try:
            return (
                int(order_count) >= self.MIN_ADVERTISER_ORDER_COUNT
                and float(finish_rate) >= self.MIN_ADVERTISER_FINISH_RATE
            )
        except (TypeError, ValueError):
            return False

    def _best_binance_price(
        self, data: dict[str, Any], trade_type: str
    ) -> tuple[Decimal | None, dict[str, Any], str]:
        """Mejor precio P2P segun el lado de la operacion.

        tradeType=BUY (compramos USDT) -> el mejor precio es el mas BAJO que
        alguien pide por vender. tradeType=SELL (vendemos USDT) -> el mejor
        precio es el mas ALTO que alguien ofrece pagar. Tomar siempre el
        minimo (como se hacia antes) daba el peor precio posible del lado
        sell -- ver caso real: Binance mostraba venta a Bs 12,46 (el precio
        mas alto, el correcto) mientras nosotros guardabamos Bs 12,44 (el
        mas bajo de los 20 anuncios). La propia API ya devuelve los anuncios
        ordenados "mejor primero" por lado, pero calculamos el extremo
        explicitamente en vez de confiar en el orden.

        Antes de tomar ese extremo, se descartan anunciantes poco confiables
        (_is_reliable_advertiser) -- si eso deja el lote vacio (mercado muy
        delgado en ese momento), se cae de vuelta al lote completo sin
        filtrar en vez de perder el dato de esa corrida; `selection` indica
        cual de los dos casos paso, para poder auditarlo despues.
        """

        candidates = []
        for item in data.get("data") or []:
            adv = item.get("adv") or {}
            price = self._parse_decimal(adv.get("price"))
            if price is None:
                continue
            candidates.append((price, item))

        if not candidates:
            return None, {}, "none"

        reliable_candidates = [
            candidate for candidate in candidates if self._is_reliable_advertiser(candidate[1])
        ]
        used_fallback = not reliable_candidates
        pool = candidates if used_fallback else reliable_candidates

        if trade_type == "SELL":
            price, item = max(pool, key=lambda candidate: candidate[0])
            selection = "highest_price"
        else:
            price, item = min(pool, key=lambda candidate: candidate[0])
            selection = "lowest_price"

        if used_fallback:
            selection += "_unfiltered_fallback"
            logger.warning(
                f"Ningun anunciante confiable para tradeType={trade_type}, "
                f"usando el lote completo sin filtrar ({len(candidates)} anuncios)"
            )

        return price, item, selection

    def _infer_bcb_unit(self, group_name: str, subtitle: str) -> str | None:
        text = self._strip_accents(f"{group_name} {subtitle}".lower())
        if "%" in text or "tasa" in text or "inflacion" in text:
            return "%"
        if "ufv" in text:
            return "BOB"
        if "oro" in text:
            return "USD / O.T.F."
        if "dolar" in text:
            return "BOB per USD"
        return None

    def _infer_bcb_market(
        self,
        group_name: str,
        subtitle: str,
        label: str = "",
    ) -> tuple[str | None, str | None]:
        text = self._strip_accents(f"{group_name} {subtitle} {label}".lower())
        if "%" in text or "tasa" in text or "inflacion" in text:
            return None, None
        if "dolar" in text:
            return "BOB", "USD"
        if "oro" in text:
            return "USD", "GOLD"
        if "ufv" in text:
            return "BOB", "UFV"
        return None, None

    def _normalize_side(self, label: str) -> str | None:
        normalized = label.strip().lower()
        if normalized == "compra":
            return "buy"
        if normalized == "venta":
            return "sell"
        return None

    def _parse_spanish_date(self, text: str) -> date | None:
        text = self._normalize_space(text.lower())
        match = re.search(r"(\d{1,2})\s+de\s+([a-záéíóúñ]+)(?:,|\s+de)?\s+(\d{4})", text)
        if not match:
            return None

        day = int(match.group(1))
        month = self.MONTHS_ES.get(self._strip_accents(match.group(2)))
        year = int(match.group(3))
        if not month:
            return None

        try:
            return date(year, month, day)
        except ValueError:
            return None

    def _parse_decimal(self, value: Any) -> Decimal | None:
        if value is None:
            return None

        text = self._clean_text(str(value))
        text = re.sub(r"[^\d,.\-]", "", text)
        if not text:
            return None

        if "," in text and "." in text:
            text = text.replace(".", "").replace(",", ".")
        elif "," in text:
            text = text.replace(",", ".")

        try:
            return Decimal(text)
        except InvalidOperation:
            return None

    def _clean_text(self, element_or_text: Any) -> str:
        if element_or_text is None:
            return ""
        if hasattr(element_or_text, "get_text"):
            text = element_or_text.get_text(" ", strip=True)
        else:
            text = str(element_or_text)
        return self._normalize_space(text)

    def _normalize_space(self, text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()

    def _strip_accents(self, text: str) -> str:
        replacements = str.maketrans("áéíóúñ", "aeioun")
        text = text.translate(replacements)
        normalized = unicodedata.normalize("NFKD", text)
        return "".join(char for char in normalized if not unicodedata.combining(char))

    def _slugify(self, text: str) -> str:
        text = self._strip_accents(text.lower())
        text = re.sub(r"[^a-z0-9]+", "_", text)
        return text.strip("_")
