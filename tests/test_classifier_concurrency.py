"""Tests for bounded concurrency in the classifier's AI-review fallback.

`classify_batch_async` used to review one eligible article with the LLM at a
time, even after the review quota (`max_articles_per_batch`) had already
narrowed the list down. Same category of fix as the scraper/summarizer/
delivery concurrency: a semaphore now caps how many LLM reviews are in
flight at once, without changing which articles get reviewed or their
final category.
"""

import asyncio

import pytest

from src.processors.classifier import NewsClassifier


def _low_confidence_article(idx: int) -> dict:
    return {
        "title": f"Comision de penal y memoria del sistema {idx}",
        "description": "La autoridad reporto perdida de datos",
        "content": "",
        "category": "general",
    }


class SlowLLM:
    def __init__(self, on_call=None):
        self._on_call = on_call

    async def chat(self, prompt, **kwargs):
        if self._on_call:
            await self._on_call()
        return '{"category": "politica", "confidence": 0.9, "reason": "test"}'


@pytest.mark.asyncio
async def test_classify_batch_async_never_exceeds_the_ai_fallback_concurrency_limit():
    in_flight = 0
    max_in_flight = 0
    lock = asyncio.Lock()

    async def track():
        nonlocal in_flight, max_in_flight
        async with lock:
            in_flight += 1
            max_in_flight = max(max_in_flight, in_flight)
        await asyncio.sleep(0.05)
        async with lock:
            in_flight -= 1

    llm = SlowLLM(on_call=track)
    classifier = NewsClassifier(llm_provider=llm)
    classifier.ai_fallback["max_articles_per_batch"] = 10
    classifier.ai_fallback["concurrency"] = 3

    articles = [_low_confidence_article(i) for i in range(8)]
    result = await classifier.classify_batch_async(articles)

    assert all(a["category"] == "politica" for a in result)
    assert max_in_flight <= 3
    # confirma que de verdad hubo solapamiento (no quedo serializado por accidente)
    assert max_in_flight >= 2


@pytest.mark.asyncio
async def test_classify_batch_async_defaults_to_four_when_concurrency_missing():
    llm = SlowLLM()
    classifier = NewsClassifier(llm_provider=llm)
    classifier.ai_fallback["max_articles_per_batch"] = 5
    del classifier.ai_fallback["concurrency"]

    articles = [_low_confidence_article(i) for i in range(3)]
    result = await classifier.classify_batch_async(articles)

    assert all(a["category"] == "politica" for a in result)


@pytest.mark.asyncio
async def test_classify_batch_async_isolates_one_review_failing_from_the_rest():
    class FlakyLLM:
        async def chat(self, prompt, **kwargs):
            if "Comision de penal y memoria del sistema 1" in prompt:
                raise RuntimeError("proveedor caido")
            return '{"category": "politica", "confidence": 0.9, "reason": "test"}'

    classifier = NewsClassifier(llm_provider=FlakyLLM())
    classifier.ai_fallback["max_articles_per_batch"] = 5

    articles = [_low_confidence_article(i) for i in range(3)]
    result = await classifier.classify_batch_async(articles)

    # el que fallo se queda con la clasificacion de reglas (sin excepcion
    # propagada), los otros dos si se actualizan via LLM.
    assert result[0]["category"] == "politica"
    assert result[1]["category_method"] == "rules_low_confidence"
    assert "category_llm_error" in result[1]
    assert result[2]["category"] == "politica"
