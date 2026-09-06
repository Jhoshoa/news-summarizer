"""Tests for bounded concurrency in per-category summarization.

Before this, `_build_summaries` summarized one category at a time, each a
full LLM round-trip (quality tier, up to MIN_MAX_TOKENS+ tokens, possible
halved retry). With ~10 categories per run this serialized 10+ LLM calls.
Same category of fix already applied to the scraper and to subscriber
delivery: a semaphore now caps how many categories are summarized at once,
without changing the resulting summaries or their order.
"""

import asyncio
from types import SimpleNamespace

import pytest

from src.main import NewsSummarizerApp


def _settings(**overrides):
    base = dict(
        summary_candidates_per_category=8,
        summary_candidates_extended_limit=8,
        summary_candidates_extended_categories="politica, economia",
        categories_list=["politica", "economia", "deportes"],
        news_cache_ttl_minutes=60,
        news_min_articles=20,
        summary_concurrency=2,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _category_from_prompt(prompt: str, categories: list[str]) -> str:
    """Los prompts reales terminan con un ejemplo de esquema JSON que
    incluye texto libre (titulos, descripciones, otro "category": "..."
    de ejemplo) -- no es seguro extraer la categoria real con un split
    generico. Como las categorias de prueba son unicas entre si, alcanza
    con buscar cual aparece en el encabezado del prompt."""

    for category in categories:
        if f"noticias de {category.upper()} en" in prompt:
            return category
    raise AssertionError(f"No se pudo identificar la categoria en el prompt: {prompt[:80]!r}")


def _article(category: str, idx: int) -> dict:
    return {
        "id": idx,
        "category": category,
        "title": f"Noticia {category} {idx}",
        "score": 1.0,
    }


@pytest.mark.asyncio
async def test_build_summaries_never_exceeds_the_summary_concurrency_limit():
    categories = ["politica", "economia", "deportes", "tecnologia", "salud"]
    news = [_article(c, i) for i, c in enumerate(categories)]

    app = NewsSummarizerApp(_settings(summary_concurrency=2))
    app.db = None

    in_flight = 0
    max_in_flight = 0
    lock = asyncio.Lock()

    class SlowLLM:
        provider = "fake"
        models = {"quality": "fake-quality"}

        async def chat(self, prompt, **kwargs):
            nonlocal in_flight, max_in_flight
            async with lock:
                in_flight += 1
                max_in_flight = max(max_in_flight, in_flight)
            await asyncio.sleep(0.05)
            async with lock:
                in_flight -= 1
            category = _category_from_prompt(prompt, categories)
            return (
                f'[{{"article_id": 0, "title": "T", "summary": "S", '
                f'"fact": "F", "category": "{category}"}}]'
            )

    app.llm = SlowLLM()

    summaries = await app._build_summaries(news, categories)

    assert len(summaries) == len(categories)
    assert max_in_flight <= 2
    # confirma que de verdad hubo solapamiento (no quedo serializado por accidente)
    assert max_in_flight >= 2


@pytest.mark.asyncio
async def test_build_summaries_preserves_category_order_regardless_of_completion_order():
    categories = ["politica", "economia", "deportes"]
    news = [_article(c, i) for i, c in enumerate(categories)]

    app = NewsSummarizerApp(_settings(summary_concurrency=3))
    app.db = None

    class VariableDelayLLM:
        provider = "fake"
        models = {"quality": "fake-quality"}

        async def chat(self, prompt, **kwargs):
            # "politica" es la mas lenta -- si el orden dependiera de cuando
            # termina cada una, quedaria al final del resultado
            delay = 0.05 if "POLITICA" in prompt else 0.01
            await asyncio.sleep(delay)
            category = _category_from_prompt(prompt, categories)
            return (
                f'[{{"article_id": 0, "title": "T-{category}", "summary": "S", '
                f'"category": "{category}"}}]'
            )

    app.llm = VariableDelayLLM()

    summaries = await app._build_summaries(news, categories)

    assert [s["category"] for s in summaries] == categories


@pytest.mark.asyncio
async def test_build_summaries_isolates_one_category_failing_from_the_rest():
    categories = ["politica", "economia", "deportes"]
    news = [_article(c, i) for i, c in enumerate(categories)]

    app = NewsSummarizerApp(_settings())
    app.db = None

    class FlakyLLM:
        provider = "fake"
        models = {"quality": "fake-quality"}

        async def chat(self, prompt, **kwargs):
            if "ECONOMIA" in prompt:
                raise RuntimeError("proveedor caido")
            category = _category_from_prompt(prompt, categories)
            return (
                f'[{{"article_id": 0, "title": "T", "summary": "S", '
                f'"category": "{category}"}}]'
            )

    app.llm = FlakyLLM()

    summaries = await app._build_summaries(news, categories)

    assert {s["category"] for s in summaries} == {"politica", "deportes"}


@pytest.mark.asyncio
async def test_build_summaries_defaults_to_four_when_setting_missing():
    categories = ["politica"]
    news = [_article("politica", 0)]

    settings = _settings()
    del settings.summary_concurrency
    app = NewsSummarizerApp(settings)
    app.db = None

    class SimpleLLM:
        provider = "fake"
        models = {"quality": "fake-quality"}

        async def chat(self, prompt, **kwargs):
            return '[{"article_id": 0, "title": "T", "summary": "S", "category": "politica"}]'

    app.llm = SimpleLLM()

    summaries = await app._build_summaries(news, categories)

    assert len(summaries) == 1
