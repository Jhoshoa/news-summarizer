import pytest

from src.processors.story_deduplicator import AIStoryDeduplicator


class FakeLLM:
    def __init__(self, response: str = "[]", *, raise_error: bool = False):
        self.response = response
        self.raise_error = raise_error
        self.last_prompt: str | None = None
        self.last_kwargs: dict | None = None

    async def chat(self, prompt: str, **kwargs: object) -> str:
        self.last_prompt = prompt
        self.last_kwargs = kwargs
        if self.raise_error:
            msg = "LLM error"
            raise RuntimeError(msg)
        return self.response


ARTICULO_DEUDA_A = {
    "article_id": 101,
    "title": "Deuda externa de Bolivia aumenta a mas de $us 14.400 millones hasta mayo de 2026",
    "source": "Radio Fides",
    "category": "economia",
    "description": "El Banco Central de Bolivia reporto que la deuda externa alcanzo los 14.400 millones de dolares hasta mayo de 2026, segun el ultimo informe.",
}

ARTICULO_DEUDA_B = {
    "article_id": 102,
    "title": "La deuda externa de Bolivia llega a los 14.418,1 millones de dolares hasta mayo de 2026",
    "source": "El Deber",
    "category": "economia",
    "description": "La deuda externa boliviana se situo en 14.418,1 millones de dolares al cierre de mayo de 2026, de acuerdo con datos del BCB.",
}

ARTICULO_INFLACION = {
    "article_id": 103,
    "title": "Inflacion en Bolivia cierra en 3.2% en el primer semestre de 2026",
    "source": "La Razon",
    "category": "economia",
    "description": "La inflacion acumulada en Bolivia alcanzo el 3.2% durante los primeros seis meses del ano, segun el INE.",
}

ARTICULO_CLASIFICA = {
    "article_id": 104,
    "title": "Bolivia clasifica al Mundial 2030 tras vencer a Uruguay",
    "source": "Ole",
    "category": "deportes",
    "description": "La seleccion boliviana de futbol logro la clasificacion al Mundial 2030 despues de una victoria historica.",
}


@pytest.mark.asyncio
async def test_deduplicate_empty_list():
    llm = FakeLLM()
    dedup = AIStoryDeduplicator(llm)
    assert await dedup.deduplicate([]) == []


@pytest.mark.asyncio
async def test_deduplicate_single_article():
    llm = FakeLLM()
    dedup = AIStoryDeduplicator(llm)
    result = await dedup.deduplicate([ARTICULO_DEUDA_A])
    assert result == [ARTICULO_DEUDA_A]


@pytest.mark.asyncio
async def test_deduplicate_keeps_unique_stories():
    llm = FakeLLM(response="[]")
    dedup = AIStoryDeduplicator(llm)
    articles = [ARTICULO_DEUDA_A, ARTICULO_INFLACION, ARTICULO_CLASIFICA]
    result = await dedup.deduplicate(articles)
    assert result == articles


@pytest.mark.asyncio
async def test_deduplicate_removes_duplicate_story():
    llm = FakeLLM(response="[1]")
    dedup = AIStoryDeduplicator(llm)
    articles = [ARTICULO_DEUDA_A, ARTICULO_DEUDA_B, ARTICULO_INFLACION]
    result = await dedup.deduplicate(articles)
    assert result == [ARTICULO_DEUDA_A, ARTICULO_INFLACION]


@pytest.mark.asyncio
async def test_deduplicate_preserves_original_fields_on_kept_article():
    llm = FakeLLM(response="[0]")
    dedup = AIStoryDeduplicator(llm)
    articles = [ARTICULO_DEUDA_B, ARTICULO_DEUDA_A, ARTICULO_INFLACION]
    result = await dedup.deduplicate(articles)
    assert len(result) == 2
    assert result[0] is ARTICULO_DEUDA_A
    assert result[0]["article_id"] == 101
    assert result[0]["title"] == ARTICULO_DEUDA_A["title"]


@pytest.mark.asyncio
async def test_deduplicate_handles_llm_error_gracefully():
    llm = FakeLLM(raise_error=True)
    dedup = AIStoryDeduplicator(llm)
    articles = [ARTICULO_DEUDA_A, ARTICULO_DEUDA_B]
    result = await dedup.deduplicate(articles)
    assert result == articles


@pytest.mark.asyncio
async def test_deduplicate_handles_invalid_json_response():
    llm = FakeLLM(response="esto no es json")
    dedup = AIStoryDeduplicator(llm)
    articles = [ARTICULO_DEUDA_A, ARTICULO_INFLACION]
    result = await dedup.deduplicate(articles)
    assert result == articles


@pytest.mark.asyncio
async def test_deduplicate_handles_empty_json_response():
    llm = FakeLLM(response="")
    dedup = AIStoryDeduplicator(llm)
    articles = [ARTICULO_DEUDA_A, ARTICULO_INFLACION]
    result = await dedup.deduplicate(articles)
    assert result == articles


@pytest.mark.asyncio
async def test_deduplicate_multiple_groups():
    llm = FakeLLM(response="[1, 3]")
    dedup = AIStoryDeduplicator(llm)
    articles = [
        ARTICULO_DEUDA_A,
        ARTICULO_DEUDA_B,
        {"article_id": 105, "title": "Gobierno anuncia nuevo bono Juancito Pinto", "source": "ABI", "category": "social", "description": "El gobierno anuncio el pago del bono Juancito Pinto para 2026."},
        {"article_id": 106, "title": "Bono Juancito Pinto 2026: todo lo que necesitas saber", "source": "El Diario", "category": "social", "description": "Detalles del bono Juancito Pinto que se pagara este ano."},
    ]
    result = await dedup.deduplicate(articles)
    assert len(result) == 2


def test_parse_indices_valid_json():
    dedup = AIStoryDeduplicator(object())
    assert dedup._parse_indices("[1, 3]", 5) == {1, 3}


def test_parse_indices_single_index():
    dedup = AIStoryDeduplicator(object())
    assert dedup._parse_indices("[2]", 5) == {2}


def test_parse_indices_json_in_text():
    dedup = AIStoryDeduplicator(object())
    response = "Los indices a descartar son [0, 2] segun el analisis."
    assert dedup._parse_indices(response, 5) == {0, 2}


def test_parse_indices_out_of_bounds_ignored():
    dedup = AIStoryDeduplicator(object())
    assert dedup._parse_indices("[1, 99]", 3) == {1}


def test_parse_indices_empty():
    dedup = AIStoryDeduplicator(object())
    assert dedup._parse_indices("[]", 5) == set()


def test_parse_indices_empty_response():
    dedup = AIStoryDeduplicator(object())
    assert dedup._parse_indices("", 5) == set()


def test_parse_indices_none():
    dedup = AIStoryDeduplicator(object())
    assert dedup._parse_indices("[0, 1, 2]", 3) == {0, 1, 2}


def test_parse_indices_code_block_json():
    dedup = AIStoryDeduplicator(object())
    response = "```json\n[0, 2]\n```"
    assert dedup._parse_indices(response, 5) == {0, 2}


def test_build_prompt_includes_article_details():
    dedup = AIStoryDeduplicator(object())
    articles = [ARTICULO_DEUDA_A, ARTICULO_INFLACION]
    prompt = dedup._build_prompt(articles)
    assert "[0]" in prompt
    assert "[1]" in prompt
    assert ARTICULO_DEUDA_A["title"] in prompt
    assert ARTICULO_INFLACION["title"] in prompt
    assert "Radio Fides" in prompt
    assert "La Razon" in prompt


def test_build_prompt_truncates_long_content():
    dedup = AIStoryDeduplicator(object())
    long_desc = "x" * 500
    articles = [{"title": "Test", "source": "Src", "category": "gen", "description": long_desc}]
    prompt = dedup._build_prompt(articles)
    assert "..." in prompt


@pytest.mark.asyncio
async def test_deduplicate_passes_correct_kwargs():
    llm = FakeLLM(response="[]")
    dedup = AIStoryDeduplicator(llm)
    await dedup.deduplicate([ARTICULO_DEUDA_A, ARTICULO_INFLACION])
    assert llm.last_kwargs is not None
    assert llm.last_kwargs.get("quality") == "fast"
    assert llm.last_kwargs.get("temperature") == 0.1
    assert llm.last_kwargs.get("max_tokens") == 1000


@pytest.mark.asyncio
async def test_deduplicate_prompt_includes_all_articles():
    llm = FakeLLM(response="[]")
    dedup = AIStoryDeduplicator(llm)
    articles = [ARTICULO_DEUDA_A, ARTICULO_DEUDA_B, ARTICULO_INFLACION, ARTICULO_CLASIFICA]
    await dedup.deduplicate(articles)
    assert llm.last_prompt is not None
    for i in range(len(articles)):
        assert f"[{i}]" in llm.last_prompt


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        ("[0]", {0}),
        ("[1, 2]", {1, 2}),
        ("[]", set()),
        ("  [0, 3]  ", {0, 3}),
        ("json\n[0]\n", {0}),
        ("```\n[1]\n```", {1}),
        ("Descarta: 0 y 2", {0, 2}),
        ("indices: 1, 3", {1, 3}),
        ("[0, 1, 2, 3, 4]", {0, 1, 2, 3, 4}),
    ],
)
def test_parse_indices_various_formats(response, expected):
    dedup = AIStoryDeduplicator(object())
    assert dedup._parse_indices(response, 5) == expected
