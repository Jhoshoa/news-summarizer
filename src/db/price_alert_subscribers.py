from __future__ import annotations

from sqlalchemy import Column, DateTime, String, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from .repository import Base, _now_bolivia


class PriceAlertSubscriber(Base):
    """Chat de Telegram suscripto a las alertas de precio del bot separado
    (PRICE_ALERT_BOT_TOKEN). Una fila por chat, sin historial: /start en el
    bot registra y /baja borra la fila (ver PriceAlertNotifier). Es una
    tabla propia, aparte de `subscribers` (noticias), porque mezclar ambos
    bots en la misma suscripcion no deja distinguir quién quiere alertas
    de precio de quién quiere briefs de noticias.
    """

    __tablename__ = "price_alert_subscribers"

    telegram_id = Column(String(50), primary_key=True)
    created_at = Column(DateTime, nullable=False, default=_now_bolivia)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=_now_bolivia,
        onupdate=_now_bolivia,
    )


class PriceAlertSubscriberRepository:
    def __init__(self, session_maker: async_sessionmaker):
        self.session_maker = session_maker

    async def add(self, telegram_id: str) -> None:
        """Upsert manual (get + add/actualizar) -- portable entre Postgres y
        SQLite (ver test_price_alert_subscribers.py), igual que
        PriceAlertRepository."""
        async with self.session_maker() as session:
            row = await session.get(PriceAlertSubscriber, telegram_id)
            if row is None:
                session.add(PriceAlertSubscriber(telegram_id=telegram_id))
            else:
                row.updated_at = _now_bolivia()
            await session.commit()

    async def remove(self, telegram_id: str) -> None:
        async with self.session_maker() as session:
            row = await session.get(PriceAlertSubscriber, telegram_id)
            if row is not None:
                await session.delete(row)
                await session.commit()

    async def is_subscribed(self, telegram_id: str) -> bool:
        async with self.session_maker() as session:
            row = await session.get(PriceAlertSubscriber, telegram_id)
            return row is not None

    async def list_chat_ids(self) -> list[str]:
        async with self.session_maker() as session:
            result = await session.execute(select(PriceAlertSubscriber.telegram_id))
            return [str(row[0]) for row in result]
