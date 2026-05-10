from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Column,
    Date,
    DateTime,
    Integer,
    Numeric,
    String,
    func,
    select,
)
from sqlalchemy.ext.asyncio import async_sessionmaker

from .repository import Base


class EconomicIndicatorValue(Base):
    __tablename__ = "economic_indicator_values"

    id = Column(Integer, primary_key=True)
    source = Column(String(50), nullable=False, index=True)
    indicator_code = Column(String(160), nullable=False, index=True)
    indicator_name = Column(String(250), nullable=False)
    indicator_group = Column(String(250), nullable=False, index=True)
    value = Column(Numeric(18, 6), nullable=False)
    unit = Column(String(80), nullable=True)
    currency = Column(String(20), nullable=True)
    asset = Column(String(20), nullable=True)
    side = Column(String(20), nullable=True, index=True)
    observed_at = Column(Date, nullable=True, index=True)
    collected_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    snapshot_key = Column(String(64), nullable=False, index=True)
    raw_payload = Column(JSON, nullable=False, default=dict)


class EconomicIndicatorRepository:
    def __init__(self, session_maker: async_sessionmaker):
        self.session_maker = session_maker

    async def save_values(self, indicators: list[dict[str, Any]]) -> dict[str, int]:
        inserted = 0
        unchanged = 0
        skipped = 0

        async with self.session_maker() as session:
            for indicator in indicators:
                value = indicator.get("value")
                if value is None:
                    skipped += 1
                    continue

                normalized = self._normalize_indicator(indicator)
                existing = await self._get_latest_matching_value(session, normalized)
                if existing and self._same_day(existing, normalized) and self._same_value(
                    existing.value,
                    normalized["value"],
                ):
                    unchanged += 1
                    continue

                row = EconomicIndicatorValue(
                    source=normalized["source"],
                    indicator_code=normalized["indicator_code"],
                    indicator_name=normalized["indicator_name"],
                    indicator_group=normalized["indicator_group"],
                    value=normalized["value"],
                    unit=normalized["unit"],
                    currency=normalized["currency"],
                    asset=normalized["asset"],
                    side=normalized["side"],
                    observed_at=normalized["observed_at"],
                    collected_at=normalized["collected_at"],
                    snapshot_key=normalized["snapshot_key"],
                    raw_payload=self._normalize_payload(normalized["raw_payload"]),
                )
                session.add(row)
                inserted += 1

            await session.commit()

        return {"inserted": inserted, "unchanged": unchanged, "skipped": skipped}

    async def get_latest_values(self, target_date: date | None = None) -> list[dict[str, Any]]:
        async with self.session_maker() as session:
            day_expression = func.coalesce(
                EconomicIndicatorValue.observed_at,
                func.date(EconomicIndicatorValue.collected_at),
            )
            latest_ids = (
                select(func.max(EconomicIndicatorValue.id).label("id"))
                .group_by(
                    EconomicIndicatorValue.source,
                    EconomicIndicatorValue.indicator_code,
                    EconomicIndicatorValue.currency,
                    EconomicIndicatorValue.asset,
                    EconomicIndicatorValue.side,
                )
                .subquery()
            )
            if target_date:
                latest_ids = (
                    select(func.max(EconomicIndicatorValue.id).label("id"))
                    .where(day_expression == target_date)
                    .group_by(
                        EconomicIndicatorValue.source,
                        EconomicIndicatorValue.indicator_code,
                        EconomicIndicatorValue.currency,
                        EconomicIndicatorValue.asset,
                        EconomicIndicatorValue.side,
                    )
                    .subquery()
                )
            stmt = (
                select(EconomicIndicatorValue)
                .join(latest_ids, EconomicIndicatorValue.id == latest_ids.c.id)
                .order_by(
                    EconomicIndicatorValue.source.asc(),
                    EconomicIndicatorValue.indicator_group.asc(),
                    EconomicIndicatorValue.indicator_name.asc(),
                )
            )
            result = await session.execute(stmt)
            rows = list(result.scalars().all())

        return [self._row_to_dict(row) for row in rows]

    async def _get_latest_matching_value(
        self,
        session,
        indicator: dict[str, Any],
    ) -> EconomicIndicatorValue | None:
        stmt = (
            select(EconomicIndicatorValue)
            .where(
                EconomicIndicatorValue.source == indicator["source"],
                EconomicIndicatorValue.indicator_code == indicator["indicator_code"],
                self._nullable_equals(EconomicIndicatorValue.currency, indicator["currency"]),
                self._nullable_equals(EconomicIndicatorValue.asset, indicator["asset"]),
                self._nullable_equals(EconomicIndicatorValue.side, indicator["side"]),
            )
            .order_by(EconomicIndicatorValue.collected_at.desc(), EconomicIndicatorValue.id.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    def _nullable_equals(self, column, value):
        if value is None:
            return column.is_(None)
        return column == value

    def _normalize_indicator(self, indicator: dict[str, Any]) -> dict[str, Any]:
        return {
            "source": str(indicator.get("source") or "unknown"),
            "indicator_code": str(indicator.get("indicator_code") or "unknown"),
            "indicator_name": str(indicator.get("indicator_name") or "unknown"),
            "indicator_group": str(indicator.get("indicator_group") or "unknown"),
            "value": self._coerce_decimal(indicator.get("value")),
            "unit": indicator.get("unit"),
            "currency": indicator.get("currency"),
            "asset": indicator.get("asset"),
            "side": indicator.get("side"),
            "observed_at": indicator.get("observed_at"),
            "collected_at": indicator.get("collected_at") or datetime.utcnow(),
            "snapshot_key": str(indicator.get("snapshot_key") or ""),
            "raw_payload": indicator.get("raw_payload") or {},
        }

    def _same_day(self, existing: EconomicIndicatorValue, indicator: dict[str, Any]) -> bool:
        existing_day = existing.observed_at or existing.collected_at.date()
        indicator_day = indicator["observed_at"] or indicator["collected_at"].date()
        return existing_day == indicator_day

    def _same_value(self, existing_value: Decimal, new_value: Decimal) -> bool:
        return Decimal(existing_value).normalize() == Decimal(new_value).normalize()

    def _coerce_decimal(self, value: Any) -> Decimal:
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))

    def _row_to_dict(self, row: EconomicIndicatorValue) -> dict[str, Any]:
        return {
            "id": row.id,
            "source": row.source,
            "indicator_code": row.indicator_code,
            "indicator_name": row.indicator_name,
            "indicator_group": row.indicator_group,
            "value": float(row.value) if isinstance(row.value, Decimal) else row.value,
            "unit": row.unit,
            "currency": row.currency,
            "asset": row.asset,
            "side": row.side,
            "observed_at": row.observed_at,
            "collected_at": row.collected_at,
            "snapshot_key": row.snapshot_key,
            "raw_payload": row.raw_payload,
        }

    def _normalize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {key: self._json_safe_value(value) for key, value in payload.items()}

    def _json_safe_value(self, value: Any) -> Any:
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, datetime | date):
            return value.isoformat()
        if isinstance(value, dict):
            return {key: self._json_safe_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._json_safe_value(item) for item in value]
        return value
