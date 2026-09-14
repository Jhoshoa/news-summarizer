from __future__ import annotations

import secrets
from datetime import timedelta
from typing import Any

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String
from sqlalchemy.ext.asyncio import async_sessionmaker

from .repository import Base, _now_bolivia

DEFAULT_LINK_TTL_SECONDS = 600


class TelegramLinkToken(Base):
    __tablename__ = "telegram_link_tokens"

    token = Column(String(64), primary_key=True)
    categories = Column(JSON, nullable=False, default=list)
    frequency = Column(String(20), nullable=False, default="diario")
    preferred_hour = Column(Integer, nullable=False, default=9)
    timezone = Column(String(50), nullable=False, default="America/La_Paz")
    consent_accepted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=_now_bolivia)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)


class TelegramLinkRepository:
    """Tokens de un solo uso para el deep link `t.me/<bot>?start=<token>`.

    El formulario web guarda ahi las categorias/frecuencia/hora elegidas antes
    de mandar al usuario a Telegram; el bot los consume en `/start <token>`
    para guardar la suscripcion completa sin volver a preguntar nada. El
    caracter set generado por `secrets.token_urlsafe` (A-Za-z0-9_-) es el
    mismo que Telegram exige para el parametro `start`.
    """

    def __init__(self, session_maker: async_sessionmaker):
        self.session_maker = session_maker

    async def create_link(
        self,
        categories: set[str] | list[str],
        frequency: str,
        preferred_hour: int,
        timezone: str,
        consent_accepted: bool,
        ttl_seconds: int = DEFAULT_LINK_TTL_SECONDS,
    ) -> tuple[str, int]:
        token = secrets.token_urlsafe(24)
        now = _now_bolivia()

        async with self.session_maker() as session:
            session.add(
                TelegramLinkToken(
                    token=token,
                    categories=sorted(categories),
                    frequency=frequency,
                    preferred_hour=preferred_hour,
                    timezone=timezone,
                    consent_accepted=consent_accepted,
                    created_at=now,
                    expires_at=now + timedelta(seconds=ttl_seconds),
                )
            )
            await session.commit()

        return token, ttl_seconds

    async def consume_link(self, token: str) -> dict[str, Any] | None:
        """Devuelve las preferencias guardadas y marca el token usado.

        None si el token no existe, ya expiro, o ya se uso -- el llamador
        (el bot) debe caer al flujo normal de seleccion por botones.
        """

        async with self.session_maker() as session:
            row = await session.get(TelegramLinkToken, token)
            if not row or row.used_at is not None or row.expires_at < _now_bolivia():
                return None

            row.used_at = _now_bolivia()
            await session.commit()

            return {
                "categories": list(row.categories or []),
                "frequency": row.frequency,
                "preferred_hour": row.preferred_hour,
                "timezone": row.timezone,
                "consent_accepted": row.consent_accepted,
            }
