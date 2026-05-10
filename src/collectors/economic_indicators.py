from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx
from bs4 import BeautifulSoup
from loguru import logger


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
    BINANCE_P2P_URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

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
        collected_at = datetime.utcnow()
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
        for card in section.select(".bcb-kpi2-card"):
            indicators.extend(
                self._parse_bcb_card(
                    card,
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
            price, raw_ad = self._lowest_binance_price(data)
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
                    collected_at=collected_at or datetime.utcnow(),
                    snapshot_key=snapshot_key,
                    raw_payload={
                        "trade_type": trade_type,
                        "selection": "lowest_price",
                        "request": payload,
                        "advertisement": raw_ad,
                    },
                )
            )

        return indicators

    def _parse_bcb_card(
        self,
        card,
        *,
        snapshot_key: str | None,
        collected_at: datetime | None,
    ) -> list[EconomicIndicator]:
        group_name = self._clean_text(card.select_one(".bcb-kpi2-name"))
        subtitle = self._clean_text(card.select_one(".bcb-kpi2-sub"))
        observed_label = self._clean_text(card.select_one(".bcb-kpi2-asof"))
        observed_at = self._parse_spanish_date(observed_label)
        unit = self._infer_bcb_unit(group_name, subtitle)

        indicators = []
        for row in card.select(".bcb-row"):
            label = self._clean_text(row.select_one(".bcb-lbl"))
            value_text = self._clean_text(row.select_one(".bcb-val"))
            value = self._parse_decimal(value_text)
            if not group_name or not label or value is None:
                continue

            indicators.append(
                EconomicIndicator(
                    source="bcb",
                    indicator_code=self._slugify(f"bcb {group_name} {label}"),
                    indicator_name=label,
                    indicator_group=group_name,
                    value=value,
                    unit=unit,
                    currency="BOB" if "dólar" in f"{group_name} {subtitle}".lower() else None,
                    asset="USD" if "dólar" in f"{group_name} {subtitle}".lower() else None,
                    side=self._normalize_side(label),
                    observed_at=observed_at,
                    collected_at=collected_at or datetime.utcnow(),
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

    def _lowest_binance_price(self, data: dict[str, Any]) -> tuple[Decimal | None, dict[str, Any]]:
        candidates = []
        for item in data.get("data") or []:
            adv = item.get("adv") or {}
            price = self._parse_decimal(adv.get("price"))
            if price is None:
                continue
            candidates.append((price, item))

        if not candidates:
            return None, {}

        price, item = min(candidates, key=lambda candidate: candidate[0])
        return price, item

    def _infer_bcb_unit(self, group_name: str, subtitle: str) -> str | None:
        text = f"{group_name} {subtitle}".lower()
        if "%" in text or "tasa" in text or "inflación" in text:
            return "%"
        if "ufv" in text:
            return "BOB"
        if "oro" in text:
            return "USD / O.T.F."
        if "dólar" in text or "dolar" in text:
            return "BOB per USD"
        return None

    def _normalize_side(self, label: str) -> str | None:
        normalized = label.strip().lower()
        if normalized == "compra":
            return "buy"
        if normalized == "venta":
            return "sell"
        return None

    def _parse_spanish_date(self, text: str) -> date | None:
        text = self._normalize_space(text.lower())
        match = re.search(r"(\d{1,2})\s+de\s+([a-záéíóúñ]+),?\s+(\d{4})", text)
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
        return text.translate(replacements)

    def _slugify(self, text: str) -> str:
        text = self._strip_accents(text.lower())
        text = re.sub(r"[^a-z0-9]+", "_", text)
        return text.strip("_")
