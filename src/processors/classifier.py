from typing import Optional

from loguru import logger


class NewsClassifier:
    """Clasifica noticias por categoría usando keywords o IA."""

    CATEGORIES = {
        "economia": [
            "bolsa",
            "acciones",
            "dólar",
            "peso",
            "inflación",
            "banco",
            "tasa",
            "crecimiento",
            "PIB",
            "trade",
            "economía",
            "finanzas",
            "mercado",
            "inversión",
            "bursátil",
            "accionista",
            " Bolívar ",
            "sus",
            "ventas",
            "exportación",
        ],
        "politica": [
            "gobierno",
            "congreso",
            "ley",
            "presidente",
            "ministro",
            "elecciones",
            "votación",
            "partido",
            "político",
            "senado",
            "cámara",
            "legislativo",
            "política",
            "diputado",
            "asambleísta",
            "MAS",
            "CC",
            "Bolivia",
            " Arce ",
            " Luis ",
        ],
        "deportes": [
            "fútbol",
            "futbol",
            "liga",
            "copa",
            "gol",
            "campeonato",
            "equipo",
            "jugador",
            "torneo",
            "títulos",
            "deporte",
            "deportes",
            "nba",
            "fifa",
            "mundial",
            "selección",
            "liga profesional",
            "club",
            "partido",
            "ganar",
            "perder",
            "empate",
        ],
        "tecnologia": [
            "tech",
            "startup",
            "app",
            "inteligencia artificial",
            "IA ",
            "software",
            "digital",
            "innovación",
            "tecnología",
            "google",
            "apple",
            "microsoft",
            "meta",
            "tesla",
            "elon",
            "celular",
            "smartphone",
            "internet",
            "ciberseguridad",
        ],
        "entretenimiento": [
            "cine",
            "música",
            "película",
            "serie",
            "actor",
            "actriz",
            "concierto",
            "famoso",
            "celebridad",
            "entretenimiento",
            "netflix",
            "hollywood",
            "estreno",
            "música",
            "cantante",
            "video",
            "festival",
            "premio",
            "grammy",
            "oscar",
        ],
    }

    def __init__(self, llm_provider=None):
        self.llm = llm_provider

    def classify(self, article: dict) -> str:
        """Clasifica por keywords (método rápido)."""

        title = article.get("title", "").lower()
        description = article.get("description", "").lower()
        source = article.get("source", "").lower()
        text = f"{title} {description} {source}"

        category_scores = {}

        for category, keywords in self.CATEGORIES.items():
            score = sum(1 for kw in keywords if kw.lower() in text)
            if score > 0:
                category_scores[category] = score

        if category_scores:
            best_category = max(category_scores, key=category_scores.get)
            logger.debug(
                f"Clasificado como '{best_category}': {article.get('title', '')[:50]}"
            )
            return best_category

        return "general"

    async def classify_with_ai(self, article: dict) -> str:
        """Clasifica con IA cuando hay duda o para mejor precisión."""

        if not self.llm:
            return self.classify(article)

        prompt = f"""Clasifica esta noticia en UNA sola categoría.

Título: {article.get("title")}
Descripción: {article.get("description", "")[:200]}

Categorías disponibles: economia, politica, deportes, tecnologia, entretenimiento, general

Responde SOLO con el nombre de la categoría (una palabra)."""

        try:
            result = await self.llm.chat(prompt, quality="fast")
            category = result.strip().lower()

            valid_categories = list(self.CATEGORIES.keys()) + ["general"]
            if category in valid_categories:
                logger.debug(
                    f"IA clasificó como '{category}': {article.get('title', '')[:50]}"
                )
                return category

            return "general"

        except Exception as e:
            logger.error(f"Error en clasificación IA: {e}")
            return self.classify(article)

    def classify_batch(self, news: list[dict]) -> list[dict]:
        """Clasifica una lista de noticias."""

        for article in news:
            article["category"] = self.classify(article)

        return news
