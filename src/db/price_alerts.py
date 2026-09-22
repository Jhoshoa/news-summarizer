from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column, DateTime, Numeric, String
from sqlalchemy.ext.asyncio import async_sessionmaker

from .repository import Base, _now_bolivia


class PriceAlertState(Base):
    """Ultimo valor que disparo una alerta de precio, por indicador.

    Una sola fila por `indicator_code` (no historial): el chequeo de umbral
    siempre compara el valor actual contra "lo que ya te avisamos la ultima
    vez", no contra la corrida anterior ni contra una ventana fija de N
    corridas -- ver PriceAlertNotifier. Sin fila todavia = nunca se
    establecio una referencia para ese indicador (primera corrida).
    """

    __tablename__ = "price_alert_state"

    indicator_code = Column(String(160), primary_key=True)
    reference_value = Column(Numeric(18, 6), nullable=False)
    # Cuanto observo el dato de precio que quedo como referencia (hora real
    # de ese valor, para poder decir "Referencia de las 11:32" en el aviso).
    # Nullable por retrocompatibilidad: filas creadas antes de la migracion
    # 023 no tienen el dato, y el aviso se arma sin la hora en ese caso.
    reference_collected_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=_now_bolivia)


class PriceAlertRepository:
    def __init__(self, session_maker: async_sessionmaker):
        self.session_maker = session_maker

    async def get_reference(self, indicator_code: str) -> Decimal | None:
        async with self.session_maker() as session:
            row = await session.get(PriceAlertState, indicator_code)
            return row.reference_value if row else None

    async def get_reference_with_time(
        self, indicator_code: str
    ) -> tuple[Decimal, datetime | None] | None:
        """Referencia junto con la hora a la que se observo ese valor. Sin
        fila devuelve None; la hora puede ser None en filas previas a la
        migracion 023."""

        async with self.session_maker() as session:
            row = await session.get(PriceAlertState, indicator_code)
            if row is None:
                return None
            return row.reference_value, row.reference_collected_at

    async def set_reference(
        self,
        indicator_code: str,
        value: Decimal,
        collected_at: datetime | None = None,
    ) -> None:
        """Upsert manual (get + add/actualizar) en vez de un ON CONFLICT de
        Postgres -- los tests corren contra SQLite (ver test_price_alerts.py),
        asi que la sintaxis tiene que ser portable entre motores. `collected_at`
        es la hora real del valor que queda como referencia."""

        async with self.session_maker() as session:
            row = await session.get(PriceAlertState, indicator_code)
            if row is None:
                session.add(
                    PriceAlertState(
                        indicator_code=indicator_code,
                        reference_value=value,
                        reference_collected_at=collected_at,
                        updated_at=_now_bolivia(),
                    )
                )
            else:
                row.reference_value = value
                row.reference_collected_at = collected_at
                row.updated_at = _now_bolivia()
            await session.commit()
