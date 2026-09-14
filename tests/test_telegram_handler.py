from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
import sentry_sdk
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.db.repository import Base
from src.db.telegram_links import TelegramLinkRepository
from src.distributors.telegram_handler import TelegramHandler


def _settings(token: str | None = "fake-token"):
    return SimpleNamespace(telegram_bot_token=token)


class FakeDb:
    def __init__(self):
        self.saved: list[dict] = []
        self.unsubscribed: list[str] = []
        self.subscriptions: dict[str, dict] = {}
        self.preview_items: list[dict] = []

    async def save_subscription(self, **kwargs):
        self.saved.append(kwargs)

    async def unsubscribe(self, telegram_id):
        self.unsubscribed.append(telegram_id)

    async def get_subscriber_by_telegram_id(self, telegram_id):
        return self.subscriptions.get(telegram_id)

    async def get_preference_preview(self, categories, *, limit=5):
        return self.preview_items[:limit]


@pytest.fixture
async def db_with_telegram_links():
    """FakeDb con un `session_maker` real (sqlite en memoria) para poder
    ejercitar `_handle_start_with_token`, que arma su propio
    TelegramLinkRepository a partir de `self.db.session_maker`."""

    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    db = FakeDb()
    db.session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield db
    await engine.dispose()


def test_handler_without_token_has_no_bot():
    handler = TelegramHandler(settings=_settings(token=None))
    assert handler.bot is None


def test_handler_with_token_creates_bot():
    handler = TelegramHandler(settings=_settings())
    assert handler.bot is not None


@pytest.mark.asyncio
async def test_send_message_without_bot_returns_false_and_does_not_raise():
    handler = TelegramHandler(settings=_settings(token=None))
    result = await handler.send_message("123", "hola")
    assert result is False


@pytest.mark.asyncio
async def test_send_message_uses_bot_send_message():
    handler = TelegramHandler(settings=_settings())

    # Bot es un TelegramObject "congelado" (no se puede setattr una instancia),
    # asi que parcheamos el metodo a nivel de clase en vez de la instancia.
    with patch("telegram.Bot.send_message", new=AsyncMock(return_value=None)) as mock_send:
        result = await handler.send_message("123", "hola mundo")

    assert result is True
    mock_send.assert_awaited_once_with(chat_id="123", text="hola mundo", parse_mode="Markdown")


@pytest.mark.asyncio
async def test_send_message_returns_false_when_telegram_api_fails():
    handler = TelegramHandler(settings=_settings())

    with patch("telegram.Bot.send_message", new=AsyncMock(side_effect=RuntimeError("network down"))):
        result = await handler.send_message("123", "hola")

    assert result is False


@pytest.mark.asyncio
async def test_send_message_reports_telegram_failures_to_sentry():
    handler = TelegramHandler(settings=_settings())
    boom = RuntimeError("network down")

    with (
        patch("telegram.Bot.send_message", new=AsyncMock(side_effect=boom)),
        patch.object(sentry_sdk, "capture_exception") as mock_capture,
    ):
        result = await handler.send_message("123", "hola")

    assert result is False
    mock_capture.assert_called_once_with(boom)


@pytest.mark.asyncio
async def test_process_update_without_bot_is_a_noop():
    handler = TelegramHandler(settings=_settings(token=None))
    await handler.process_update({"update_id": 1})  # no debe lanzar


@pytest.mark.asyncio
async def test_process_update_dispatches_start_command_to_handle_message():
    db = FakeDb()
    handler = TelegramHandler(db_repository=db, settings=_settings())

    payload = {
        "update_id": 1,
        "message": {
            "message_id": 1,
            "date": 0,
            "chat": {"id": 555, "type": "private"},
            "text": "/start",
        },
    }

    # handle_message llama update.message.reply_text, que internamente usa el
    # bot adjunto por Update.de_json — parcheamos a nivel de clase para no
    # pegarle a la API real de Telegram (la instancia esta "congelada").
    with patch("telegram.Bot.send_message", new=AsyncMock(return_value=None)):
        await handler.process_update(payload)


@pytest.mark.asyncio
async def test_process_update_malformed_payload_does_not_raise():
    handler = TelegramHandler(settings=_settings())
    await handler.process_update({"not": "a valid telegram update"})


@pytest.mark.asyncio
async def test_process_update_reports_failures_to_sentry():
    handler = TelegramHandler(settings=_settings())
    boom = RuntimeError("malformed update")

    with (
        patch("telegram.Update.de_json", side_effect=boom),
        patch.object(sentry_sdk, "capture_exception") as mock_capture,
    ):
        await handler.process_update({"update_id": 1})

    mock_capture.assert_called_once_with(boom)


@pytest.mark.asyncio
async def test_handle_selection_saves_subscription_with_categories():
    db = FakeDb()
    handler = TelegramHandler(db_repository=db, settings=_settings())

    update = SimpleNamespace(
        message=SimpleNamespace(
            text="1 3",
            chat=SimpleNamespace(id=777),
            reply_text=AsyncMock(),
        )
    )

    result = await handler._handle_selection(update, None, "777", "1 3")

    assert result == "Suscripcion guardada"
    assert db.saved == [
        {
            "telegram_id": "777",
            "channel": "telegram",
            "categories": {"economia", "deportes"},
            "consent_accepted": True,
        }
    ]
    # sin esto, nadie se entera de que /noticias existe
    assert "/noticias" in update.message.reply_text.await_args.args[0]


@pytest.mark.asyncio
async def test_handle_cancel_unsubscribes_via_db():
    db = FakeDb()
    handler = TelegramHandler(db_repository=db, settings=_settings())

    update = SimpleNamespace(
        message=SimpleNamespace(chat=SimpleNamespace(id=888), reply_text=AsyncMock())
    )

    result = await handler._handle_cancel(update, None)

    assert result == "Dado de baja"
    assert db.unsubscribed == ["888"]


@pytest.mark.asyncio
async def test_callback_query_tap_saves_subscription_and_answers_the_query():
    """Regression test: the inline category buttons (`_show_categories`) send
    a callback_query update, not a message -- handle_message used to check
    only `update.message` and silently no-op on button taps."""

    db = FakeDb()
    handler = TelegramHandler(db_repository=db, settings=_settings())

    update = SimpleNamespace(
        callback_query=SimpleNamespace(
            data="cat_3",
            answer=AsyncMock(),
            message=SimpleNamespace(chat=SimpleNamespace(id=555), reply_text=AsyncMock()),
        ),
        message=None,
    )

    result = await handler.handle_message(update, None)

    assert result == "Suscripcion guardada"
    update.callback_query.answer.assert_awaited_once()
    update.callback_query.message.reply_text.assert_awaited_once()
    assert db.saved == [
        {
            "telegram_id": "555",
            "channel": "telegram",
            "categories": {"deportes"},
            "consent_accepted": True,
        }
    ]


@pytest.mark.asyncio
async def test_callback_query_todas_selects_every_category():
    db = FakeDb()
    handler = TelegramHandler(db_repository=db, settings=_settings())

    update = SimpleNamespace(
        callback_query=SimpleNamespace(
            data="cat_todas",
            answer=AsyncMock(),
            message=SimpleNamespace(chat=SimpleNamespace(id=555), reply_text=AsyncMock()),
        ),
        message=None,
    )

    await handler.handle_message(update, None)

    assert db.saved[0]["categories"] == {
        "economia",
        "politica",
        "deportes",
        "tecnologia",
        "entretenimiento",
    }


@pytest.mark.asyncio
async def test_start_with_valid_token_applies_web_preferences_without_asking_again(
    db_with_telegram_links,
):
    """The subscribe form's telegram QR/link carries the categories,
    frequency, and hour picked on the web as a one-use token; /start <token>
    should apply all of it immediately instead of showing the category
    picker (which only ever sets categories, not frequency/hour)."""

    repo = TelegramLinkRepository(db_with_telegram_links.session_maker)
    token, _ = await repo.create_link(
        categories={"economia", "tecnologia"},
        frequency="semanal",
        preferred_hour=20,
        timezone="America/La_Paz",
        consent_accepted=True,
    )
    handler = TelegramHandler(db_repository=db_with_telegram_links, settings=_settings())

    update = SimpleNamespace(
        callback_query=None,
        message=SimpleNamespace(
            text=f"/start {token}",
            chat=SimpleNamespace(id=999),
            reply_text=AsyncMock(),
        ),
    )

    result = await handler.handle_message(update, None)

    assert result == "Suscripcion guardada desde la web"
    update.message.reply_text.assert_awaited_once()
    assert db_with_telegram_links.saved == [
        {
            "telegram_id": "999",
            "channel": "telegram",
            "categories": {"economia", "tecnologia"},
            "frequency": "semanal",
            "preferred_hour": 20,
            "timezone": "America/La_Paz",
            "consent_accepted": True,
        }
    ]
    assert "/noticias" in update.message.reply_text.await_args.args[0]

    # el token es de un solo uso
    assert await repo.consume_link(token) is None


@pytest.mark.asyncio
async def test_start_with_unknown_token_falls_back_to_category_picker(db_with_telegram_links):
    handler = TelegramHandler(db_repository=db_with_telegram_links, settings=_settings())

    update = SimpleNamespace(
        callback_query=None,
        message=SimpleNamespace(
            text="/start no-existe-o-vencio",
            chat=SimpleNamespace(id=999),
            reply_text=AsyncMock(),
        ),
    )

    result = await handler.handle_message(update, None)

    assert result is not None
    assert "EcoBrief Bolivia" in result
    assert db_with_telegram_links.saved == []
    # aviso de codigo invalido + bienvenida + botones de categorias
    assert update.message.reply_text.await_count == 3


@pytest.mark.asyncio
async def test_bare_start_without_token_shows_category_picker_as_before(db_with_telegram_links):
    handler = TelegramHandler(db_repository=db_with_telegram_links, settings=_settings())

    update = SimpleNamespace(
        callback_query=None,
        message=SimpleNamespace(
            text="/start",
            chat=SimpleNamespace(id=999),
            reply_text=AsyncMock(),
        ),
    )

    result = await handler.handle_message(update, None)

    assert result is not None
    assert "EcoBrief Bolivia" in result
    assert db_with_telegram_links.saved == []
    # bienvenida + botones de categorias, sin el aviso de codigo invalido
    assert update.message.reply_text.await_count == 2


@pytest.mark.asyncio
def _all_reply_text_bodies(mock: AsyncMock) -> list[str]:
    return [call.args[0] for call in mock.await_args_list]


@pytest.mark.asyncio
async def test_noticias_sends_brief_for_a_subscribed_chat():
    """Sin image_url, cada noticia cae directo a texto (header + 1 card +
    footer = 3 mensajes)."""

    db = FakeDb()
    db.subscriptions["555"] = {"categories": ["deportes"], "frequency": "diario", "preferred_hour": 9}
    db.preview_items = [
        {
            "category": "deportes",
            "title": "Bolivia gana 2-0",
            "summary": "Resumen del partido de anoche.",
            "fact": "Segundo triunfo consecutivo.",
            "summary_date": "2026-09-14",
        }
    ]
    handler = TelegramHandler(db_repository=db, settings=_settings())

    update = SimpleNamespace(
        callback_query=None,
        message=SimpleNamespace(text="/noticias", chat=SimpleNamespace(id=555), reply_text=AsyncMock()),
    )

    result = await handler.handle_message(update, None)

    assert result == "Brief enviado a demanda"
    assert update.message.reply_text.await_count == 3
    bodies = _all_reply_text_bodies(update.message.reply_text)
    assert any("Bolivia gana 2-0" in body and "Segundo triunfo consecutivo." in body for body in bodies)
    assert any("/preferencias" in body for body in bodies)


@pytest.mark.asyncio
async def test_noticias_sends_item_as_photo_when_image_url_present():
    db = FakeDb()
    db.subscriptions["555"] = {"categories": ["deportes"]}
    db.preview_items = [
        {
            "category": "deportes",
            "title": "Bolivia gana 2-0",
            "summary": "Resumen del partido.",
            "fact": None,
            "image_url": "https://example.com/foto.jpg",
        }
    ]
    handler = TelegramHandler(db_repository=db, settings=_settings())

    update = SimpleNamespace(
        callback_query=None,
        message=SimpleNamespace(
            text="/noticias",
            chat=SimpleNamespace(id=555),
            reply_text=AsyncMock(),
            reply_photo=AsyncMock(),
        ),
    )

    result = await handler.handle_message(update, None)

    assert result == "Brief enviado a demanda"
    update.message.reply_photo.assert_awaited_once()
    assert update.message.reply_photo.await_args.kwargs["photo"] == "https://example.com/foto.jpg"
    assert "Bolivia gana 2-0" in update.message.reply_photo.await_args.kwargs["caption"]
    # header + footer via texto, la noticia en si via foto (no duplicada como texto)
    assert update.message.reply_text.await_count == 2


@pytest.mark.asyncio
async def test_noticias_falls_back_to_text_when_sending_the_photo_fails():
    """Un link de imagen roto/caido no debe perder la noticia -- cae a texto."""

    db = FakeDb()
    db.subscriptions["555"] = {"categories": ["deportes"]}
    db.preview_items = [
        {
            "category": "deportes",
            "title": "Bolivia gana 2-0",
            "summary": "Resumen del partido.",
            "fact": None,
            "image_url": "https://example.com/foto-rota.jpg",
        }
    ]
    handler = TelegramHandler(db_repository=db, settings=_settings())

    update = SimpleNamespace(
        callback_query=None,
        message=SimpleNamespace(
            text="/noticias",
            chat=SimpleNamespace(id=555),
            reply_text=AsyncMock(),
            reply_photo=AsyncMock(side_effect=RuntimeError("no se pudo bajar la imagen")),
        ),
    )

    result = await handler.handle_message(update, None)

    assert result == "Brief enviado a demanda"
    update.message.reply_photo.assert_awaited_once()
    bodies = _all_reply_text_bodies(update.message.reply_text)
    assert any("Bolivia gana 2-0" in body for body in bodies)


@pytest.mark.asyncio
async def test_noticias_includes_a_read_more_link_when_site_base_url_is_set():
    db = FakeDb()
    db.subscriptions["555"] = {"categories": ["deportes"]}
    db.preview_items = [
        {"category": "deportes", "title": "Bolivia gana", "summary": "", "fact": None, "article_id": 42}
    ]
    settings = SimpleNamespace(telegram_bot_token="fake-token", site_base_url="https://ecobriefbolivia.online")
    handler = TelegramHandler(db_repository=db, settings=settings)

    update = SimpleNamespace(
        callback_query=None,
        message=SimpleNamespace(text="/noticias", chat=SimpleNamespace(id=555), reply_text=AsyncMock()),
    )

    await handler.handle_message(update, None)

    bodies = _all_reply_text_bodies(update.message.reply_text)
    assert any("[Leer completo](https://ecobriefbolivia.online/article/42)" in body for body in bodies)


@pytest.mark.asyncio
async def test_noticias_omits_the_link_when_site_base_url_is_not_configured():
    db = FakeDb()
    db.subscriptions["555"] = {"categories": ["deportes"]}
    db.preview_items = [
        {"category": "deportes", "title": "Bolivia gana", "summary": "", "fact": None, "article_id": 42}
    ]
    handler = TelegramHandler(db_repository=db, settings=_settings())

    update = SimpleNamespace(
        callback_query=None,
        message=SimpleNamespace(text="/noticias", chat=SimpleNamespace(id=555), reply_text=AsyncMock()),
    )

    await handler.handle_message(update, None)

    bodies = _all_reply_text_bodies(update.message.reply_text)
    assert not any("Leer completo" in body for body in bodies)


@pytest.mark.asyncio
async def test_noticias_groups_multiple_photos_into_one_album_message():
    """Varias noticias con imagen se mandan juntas en un solo album (menos
    mensajes que una foto por noticia); la que no tiene imagen no entra al
    grupo pero igual llega, como texto."""

    db = FakeDb()
    db.subscriptions["555"] = {"categories": ["deportes"]}
    db.preview_items = [
        {
            "category": "deportes",
            "title": "Noticia A",
            "summary": "",
            "fact": None,
            "image_url": "https://example.com/a.jpg",
        },
        {
            "category": "deportes",
            "title": "Noticia B",
            "summary": "",
            "fact": None,
            "image_url": "https://example.com/b.jpg",
        },
        {"category": "deportes", "title": "Noticia C sin imagen", "summary": "", "fact": None},
    ]
    handler = TelegramHandler(db_repository=db, settings=_settings())

    update = SimpleNamespace(
        callback_query=None,
        message=SimpleNamespace(
            text="/noticias",
            chat=SimpleNamespace(id=555),
            reply_text=AsyncMock(),
            reply_photo=AsyncMock(),
            reply_media_group=AsyncMock(),
        ),
    )

    result = await handler.handle_message(update, None)

    assert result == "Brief enviado a demanda"
    update.message.reply_media_group.assert_awaited_once()
    media = update.message.reply_media_group.await_args.kwargs["media"]
    assert len(media) == 2
    assert "Noticia A" in media[0].caption
    assert "Noticia B" in media[1].caption
    update.message.reply_photo.assert_not_awaited()
    bodies = _all_reply_text_bodies(update.message.reply_text)
    assert any("Noticia C sin imagen" in body for body in bodies)


@pytest.mark.asyncio
async def test_noticias_falls_back_to_individual_photos_when_the_album_fails():
    """sendMediaGroup es todo-o-nada: si una sola imagen del album falla,
    Telegram rechaza el grupo entero -- hay que reintentar item por item
    para no perder las que si funcionan."""

    db = FakeDb()
    db.subscriptions["555"] = {"categories": ["deportes"]}
    db.preview_items = [
        {
            "category": "deportes",
            "title": "Noticia A",
            "summary": "",
            "fact": None,
            "image_url": "https://example.com/a.jpg",
        },
        {
            "category": "deportes",
            "title": "Noticia B",
            "summary": "",
            "fact": None,
            "image_url": "https://example.com/b.jpg",
        },
    ]
    handler = TelegramHandler(db_repository=db, settings=_settings())

    update = SimpleNamespace(
        callback_query=None,
        message=SimpleNamespace(
            text="/noticias",
            chat=SimpleNamespace(id=555),
            reply_text=AsyncMock(),
            reply_photo=AsyncMock(),
            reply_media_group=AsyncMock(side_effect=RuntimeError("una imagen del grupo no se pudo bajar")),
        ),
    )

    result = await handler.handle_message(update, None)

    assert result == "Brief enviado a demanda"
    update.message.reply_media_group.assert_awaited_once()
    assert update.message.reply_photo.await_count == 2


@pytest.mark.asyncio
async def test_hoy_is_an_alias_for_noticias():
    db = FakeDb()
    db.subscriptions["555"] = {"categories": ["deportes"]}
    db.preview_items = [{"category": "deportes", "title": "Bolivia gana", "summary": "", "fact": None}]
    handler = TelegramHandler(db_repository=db, settings=_settings())

    update = SimpleNamespace(
        callback_query=None,
        message=SimpleNamespace(text="/hoy", chat=SimpleNamespace(id=555), reply_text=AsyncMock()),
    )

    result = await handler.handle_message(update, None)

    assert result == "Brief enviado a demanda"


@pytest.mark.asyncio
async def test_noticias_without_subscription_asks_to_start():
    db = FakeDb()
    handler = TelegramHandler(db_repository=db, settings=_settings())

    update = SimpleNamespace(
        callback_query=None,
        message=SimpleNamespace(text="/noticias", chat=SimpleNamespace(id=999), reply_text=AsyncMock()),
    )

    result = await handler.handle_message(update, None)

    assert result == "No suscripto"
    sent_text = update.message.reply_text.await_args.args[0]
    assert "/start" in sent_text


@pytest.mark.asyncio
async def test_noticias_with_no_fresh_items_says_so():
    db = FakeDb()
    db.subscriptions["555"] = {"categories": ["deportes"]}
    db.preview_items = []
    handler = TelegramHandler(db_repository=db, settings=_settings())

    update = SimpleNamespace(
        callback_query=None,
        message=SimpleNamespace(text="/noticias", chat=SimpleNamespace(id=555), reply_text=AsyncMock()),
    )

    result = await handler.handle_message(update, None)

    assert result == "Sin noticias nuevas"


@pytest.mark.asyncio
async def test_noticias_escapes_markdown_special_characters_in_titles():
    """Un titulo real puede traer _, *, ` o [ sueltos (texto scrapeado, no
    controlado por nosotros); sin escapar rompe el parseo de Markdown y
    Telegram devuelve un error en vez de mandar el mensaje."""

    db = FakeDb()
    db.subscriptions["555"] = {"categories": ["tecnologia"]}
    db.preview_items = [
        {
            "category": "tecnologia",
            "title": "Precio_del* dolar `sube` [hoy]",
            "summary": "Texto con _guiones_bajos_ y *asteriscos*.",
            "fact": None,
        }
    ]
    handler = TelegramHandler(db_repository=db, settings=_settings())

    update = SimpleNamespace(
        callback_query=None,
        message=SimpleNamespace(text="/noticias", chat=SimpleNamespace(id=555), reply_text=AsyncMock()),
    )

    await handler.handle_message(update, None)

    bodies = _all_reply_text_bodies(update.message.reply_text)
    assert any(r"Precio\_del\* dolar \`sube\` \[hoy]" in body for body in bodies)
