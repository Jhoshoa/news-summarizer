from datetime import datetime

from loguru import logger
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    select,
)
from sqlalchemy import (
    update as sql_update,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class Subscriber(Base):
    __tablename__ = "subscribers"

    id = Column(Integer, primary_key=True)
    phone = Column(String(20), nullable=True)
    telegram_id = Column(String(20), nullable=True)
    channel = Column(String(20), default="whatsapp")
    categories = Column(JSON, default=list)
    timezone = Column(String(50), default="America/La_Paz")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    def __repr__(self):
        return f"<Subscriber {self.phone or self.telegram_id} active={self.is_active}>"


class Database:
    """Repositorio de base de datos."""

    def __init__(self, url: str):
        self.engine = create_async_engine(url, echo=False)
        self.session_maker = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        logger.info("Database inicializada")

    async def init_db(self):
        """Crea las tablas."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Tablas creadas")

    async def save_subscription(
        self,
        phone: str | None = None,
        telegram_id: str | None = None,
        channel: str = "whatsapp",
        categories: set = None,
    ) -> bool:
        """Guarda o actualiza una suscripción."""

        if not phone and not telegram_id:
            logger.error("Se requiere phone o telegram_id")
            return False

        async with self.session_maker() as session:
            stmt = select(Subscriber).where(
                (Subscriber.phone == phone)
                if phone
                else False | (Subscriber.telegram_id == telegram_id)
                if telegram_id
                else False
            )
            result = await session.execute(stmt)
            subscriber = result.scalar_one_or_none()

            if subscriber:
                subscriber.categories = (
                    list(categories) if categories else subscriber.categories
                )
                subscriber.channel = channel
                subscriber.updated_at = datetime.utcnow()
                subscriber.is_active = True
                logger.info(f"Actualizada suscripción: {phone or telegram_id}")
            else:
                subscriber = Subscriber(
                    phone=phone,
                    telegram_id=telegram_id,
                    channel=channel,
                    categories=list(categories) if categories else ["general"],
                )
                session.add(subscriber)
                logger.info(f"Nueva suscripción: {phone or telegram_id}")

            await session.commit()
            return True

    async def get_active_subscribers(self) -> list[Subscriber]:
        """Obtiene todos los subscribers activos."""

        async with self.session_maker() as session:
            stmt = select(Subscriber).where(Subscriber.is_active)
            result = await session.execute(stmt)
            subscribers = list(result.scalars().all())
            logger.info(f"Obtenidos {len(subscribers)} subscribers activos")
            return subscribers

    async def get_subscriber_by_phone(self, phone: str) -> Subscriber | None:
        """Obtiene un subscriber por teléfono."""

        async with self.session_maker() as session:
            stmt = select(Subscriber).where(Subscriber.phone == phone)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_subscriber_by_telegram(
        self, telegram_id: str
    ) -> Subscriber | None:
        """Obtiene un subscriber por telegram ID."""

        async with self.session_maker() as session:
            stmt = select(Subscriber).where(Subscriber.telegram_id == telegram_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def unsubscribe(self, identifier: str) -> bool:
        """Desactiva una suscripción."""

        async with self.session_maker() as session:
            stmt = (
                sql_update(Subscriber)
                .where(
                    (Subscriber.phone == identifier)
                    | (Subscriber.telegram_id == identifier)
                )
                .values(is_active=False, updated_at=datetime.utcnow())
            )
            await session.execute(stmt)
            await session.commit()
            logger.info(f"Desactivada suscripción: {identifier}")
            return True

    async def get_subscription_count(self) -> int:
        """Cuenta subscribers activos."""

        async with self.session_maker() as session:
            stmt = select(Subscriber).where(Subscriber.is_active)
            result = await session.execute(stmt)
            return len(list(result.scalars().all()))

    async def close(self):
        """Cierra la conexión."""
        await self.engine.dispose()
        logger.info("Database cerrada")
