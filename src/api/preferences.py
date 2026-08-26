from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator

from src.db.repository import DEFAULT_CATEGORIES

ChannelSlug = Literal["whatsapp", "telegram", "email"]
FrequencySlug = Literal["diario", "dias_habiles", "tres_veces_semana", "semanal"]

VALID_FREQUENCIES = {"diario", "dias_habiles", "tres_veces_semana", "semanal"}
# Fuera de este rango casi no hay noticias nuevas que enviar (madrugada) y el
# cron no dispara ventanas de entrega antes/despues de este rango.
MIN_PREFERRED_HOUR = 9
MAX_PREFERRED_HOUR = 23
EMAIL_PATTERN = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.IGNORECASE)


class PreferenceOption(BaseModel):
    slug: str
    label: str
    enabled: bool = True
    note: str | None = None


class PreferenceOptionsResponse(BaseModel):
    categories: list[PreferenceOption]
    channels: list[PreferenceOption]
    frequencies: list[PreferenceOption]
    preferred_hours: list[PreferenceOption]


class SubscribeRequest(BaseModel):
    channel: ChannelSlug
    phone: str | None = None
    telegram_id: str | None = None
    email: str | None = None
    categories: list[str] = Field(min_length=1)
    frequency: FrequencySlug = "diario"
    preferred_hour: int = Field(default=9, ge=MIN_PREFERRED_HOUR, le=MAX_PREFERRED_HOUR)
    timezone: str = "America/La_Paz"
    consent_accepted: bool = False

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = re.sub(r"[\s().-]+", "", value.strip())
        if normalized.startswith("00"):
            normalized = f"+{normalized[2:]}"
        if normalized and not normalized.startswith("+"):
            normalized = f"+{normalized}"
        return normalized or None

    @field_validator("telegram_id")
    @classmethod
    def normalize_telegram_id(cls, value: str | None) -> str | None:
        normalized = str(value or "").strip()
        return normalized or None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        normalized = str(value or "").strip().lower()
        if not normalized:
            return None
        if len(normalized) > 254 or not EMAIL_PATTERN.fullmatch(normalized):
            raise ValueError("Email invalido")
        return normalized

    @field_validator("categories")
    @classmethod
    def normalize_categories(cls, values: list[str]) -> list[str]:
        normalized = sorted({str(value).strip().lower() for value in values if str(value).strip()})
        invalid = [value for value in normalized if value not in DEFAULT_CATEGORIES]
        if invalid:
            raise ValueError(f"Categorias no soportadas: {', '.join(invalid)}")
        if not normalized:
            raise ValueError("Selecciona al menos una categoria")
        return normalized

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        normalized = value.strip() or "America/La_Paz"
        if not re.fullmatch(r"[A-Za-z_]+/[A-Za-z_\-]+", normalized):
            raise ValueError("Timezone invalido")
        return normalized

    @model_validator(mode="after")
    def validate_contact_and_consent(self):
        if not self.consent_accepted:
            raise ValueError("Debes aceptar recibir briefs segun tus preferencias")
        if self.channel == "whatsapp":
            if not self.phone:
                raise ValueError("WhatsApp requiere un numero de telefono")
            if not re.fullmatch(r"\+\d{8,15}", self.phone):
                raise ValueError("Telefono invalido; usa formato internacional, por ejemplo +59170000000")
        if self.channel == "telegram" and not self.telegram_id:
            raise ValueError("Telegram requiere un identificador o usar el bot configurado")
        if self.channel == "email" and not self.email:
            raise ValueError("Email requiere un correo electronico valido")
        return self


class SubscribeResponse(BaseModel):
    status: Literal["saved"]
    channel: ChannelSlug
    categories: list[str]
    frequency: str
    preferred_hour: int
    message: str


class UnsubscribeRequest(BaseModel):
    channel: ChannelSlug
    identifier: str = Field(min_length=3, max_length=80)

    @field_validator("identifier")
    @classmethod
    def strip_identifier(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Identificador requerido")
        return normalized

    @model_validator(mode="after")
    def normalize_identifier_for_channel(self):
        if self.channel == "whatsapp":
            normalized = re.sub(r"[\s().-]+", "", self.identifier)
            if normalized.startswith("00"):
                normalized = f"+{normalized[2:]}"
            if normalized.isdigit():
                normalized = f"+{normalized}"
            self.identifier = normalized
        elif self.channel == "email":
            normalized = self.identifier.lower()
            if len(normalized) > 254 or not EMAIL_PATTERN.fullmatch(normalized):
                raise ValueError("Email invalido")
            self.identifier = normalized
        return self


class UnsubscribeResponse(BaseModel):
    status: Literal["unsubscribed"]
    message: str


class PreviewRequest(BaseModel):
    categories: list[str] = Field(min_length=1)
    frequency: FrequencySlug = "diario"

    @field_validator("categories")
    @classmethod
    def normalize_categories(cls, values: list[str]) -> list[str]:
        normalized = sorted({str(value).strip().lower() for value in values if str(value).strip()})
        invalid = [value for value in normalized if value not in DEFAULT_CATEGORIES]
        if invalid:
            raise ValueError(f"Categorias no soportadas: {', '.join(invalid)}")
        if not normalized:
            raise ValueError("Selecciona al menos una categoria")
        return normalized


class PreviewItem(BaseModel):
    category: str
    title: str
    summary: str
    fact: str | None = None
    summary_date: Any | None = None


class PreviewResponse(BaseModel):
    items: list[PreviewItem]
    has_data: bool
    message: str


def _channel_options(app_instance: Any) -> list[PreferenceOption]:
    settings = getattr(app_instance, "settings", None)
    whatsapp_enabled = bool(getattr(settings, "twilio_account_sid", None))
    telegram_enabled = bool(getattr(settings, "telegram_bot_token", None))
    email_enabled = bool(getattr(settings, "email_enabled", False))
    return [
        PreferenceOption(
            slug="email",
            label="Email",
            enabled=True,
            note=None if email_enabled else "Guardado disponible; envio requiere SMTP configurado.",
        ),
        PreferenceOption(
            slug="whatsapp",
            label="WhatsApp",
            enabled=True,
            note=(
                "Disponible para demo; envio real requiere Twilio configurado."
                if not whatsapp_enabled
                else "Disponible para demo inicial; puede requerir plan premium despues."
            ),
        ),
        PreferenceOption(
            slug="telegram",
            label="Telegram",
            enabled=telegram_enabled,
            note=None if telegram_enabled else "Requiere bot de Telegram configurado.",
        ),
    ]


def create_preferences_router(get_app_instance: Callable[[], Any]) -> APIRouter:
    router = APIRouter(prefix="/api/preferences", tags=["preferences"])

    @router.get("/options", response_model=PreferenceOptionsResponse)
    async def get_preference_options():
        app_instance = get_app_instance()
        categories = [
            PreferenceOption(slug=slug, label=label)
            for slug, label in DEFAULT_CATEGORIES.items()
        ]
        frequencies = [
            PreferenceOption(slug="diario", label="Diario"),
            PreferenceOption(slug="dias_habiles", label="Dias habiles"),
            PreferenceOption(slug="tres_veces_semana", label="Tres veces por semana"),
            PreferenceOption(slug="semanal", label="Semanal"),
        ]
        preferred_hours = [
            PreferenceOption(slug=str(hour), label=f"{hour:02d}:00")
            for hour in range(MIN_PREFERRED_HOUR, MAX_PREFERRED_HOUR + 1)
        ]
        return PreferenceOptionsResponse(
            categories=categories,
            channels=_channel_options(app_instance),
            frequencies=frequencies,
            preferred_hours=preferred_hours,
        )

    @router.post("/subscribe", response_model=SubscribeResponse)
    async def subscribe(request: SubscribeRequest):
        app_instance = get_app_instance()
        if not app_instance or not app_instance.db:
            raise HTTPException(status_code=503, detail="DB no disponible")

        saved = await app_instance.db.save_subscription(
            phone=request.phone if request.channel == "whatsapp" else None,
            telegram_id=request.telegram_id if request.channel == "telegram" else None,
            email=request.email if request.channel == "email" else None,
            channel=request.channel,
            categories=set(request.categories),
            frequency=request.frequency,
            preferred_hour=request.preferred_hour,
            timezone=request.timezone,
            consent_accepted=request.consent_accepted,
        )
        if not saved:
            raise HTTPException(status_code=500, detail="No se pudo guardar la suscripcion")

        return SubscribeResponse(
            status="saved",
            channel=request.channel,
            categories=request.categories,
            frequency=request.frequency,
            preferred_hour=request.preferred_hour,
            message="Preferencias guardadas. Puedes cambiarlas o darte de baja cuando quieras.",
        )

    @router.post("/unsubscribe", response_model=UnsubscribeResponse)
    async def unsubscribe(request: UnsubscribeRequest):
        app_instance = get_app_instance()
        if not app_instance or not app_instance.db:
            raise HTTPException(status_code=503, detail="DB no disponible")

        await app_instance.db.unsubscribe(request.identifier)
        return UnsubscribeResponse(
            status="unsubscribed",
            message="Si existia una suscripcion activa, fue desactivada.",
        )

    @router.post("/preview", response_model=PreviewResponse)
    async def preview(request: PreviewRequest):
        app_instance = get_app_instance()
        if not app_instance or not app_instance.db:
            raise HTTPException(status_code=503, detail="DB no disponible")

        items = await app_instance.db.get_preference_preview(request.categories)
        return PreviewResponse(
            items=items,
            has_data=bool(items),
            message=(
                "Preview basado en briefs recientes."
                if items
                else "No hay briefs recientes para las categorias seleccionadas."
            ),
        )

    return router
