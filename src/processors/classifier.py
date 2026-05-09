import unicodedata

from loguru import logger


class NewsClassifier:
    """Clasifica noticias por categoria usando keywords o IA."""

    CATEGORIES = {
        "economia": [
            "bolsa",
            "acciones",
            "dolar",
            "peso",
            "inflacion",
            "banco",
            "tasa",
            "crecimiento",
            "pib",
            "trade",
            "economia",
            "finanzas",
            "mercado",
            "inversion",
            "bursatil",
            "accionista",
            "bolivar",
            "sus",
            "ventas",
            "exportacion",
        ],
        "politica": [
            "gobierno",
            "congreso",
            "ley",
            "presidente",
            "ministro",
            "elecciones",
            "votacion",
            "partido",
            "politico",
            "senado",
            "camara",
            "legislativo",
            "politica",
            "diputado",
            "asambleista",
            "mas",
            "cc",
            "arce",
            "luis",
        ],
        "deportes": [
            "futbol",
            "liga",
            "copa",
            "gol",
            "campeonato",
            "equipo",
            "jugador",
            "torneo",
            "titulos",
            "deporte",
            "deportes",
            "nba",
            "fifa",
            "mundial",
            "seleccion",
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
            "ia",
            "software",
            "digital",
            "innovacion",
            "tecnologia",
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
            "musica",
            "pelicula",
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
        """Clasifica por keywords."""

        title = self._normalize(article.get("title", ""))
        description = self._normalize(article.get("description", ""))
        source = self._normalize(article.get("source", ""))
        text = f"{title} {description} {source}"

        category_scores = {}

        for category, keywords in self.CATEGORIES.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                category_scores[category] = score

        if category_scores:
            best_category = max(category_scores, key=category_scores.get)
            logger.debug(
                f"Clasificado como '{best_category}': {article.get('title', '')[:50]}"
            )
            return best_category

        existing_category = self._normalize(article.get("category", "general"))
        if existing_category in self.CATEGORIES:
            return existing_category

        return "general"

    async def classify_with_ai(self, article: dict) -> str:
        """Clasifica con IA cuando hay duda o para mejor precision."""

        if not self.llm:
            return self.classify(article)

        prompt = f"""Clasifica esta noticia en UNA sola categoria.

Titulo: {article.get("title")}
Descripcion: {article.get("description", "")[:200]}

Categorias disponibles: economia, politica, deportes, tecnologia, entretenimiento, general

Responde SOLO con el nombre de la categoria (una palabra)."""

        try:
            result = await self.llm.chat(prompt, quality="fast")
            category = self._normalize(result.strip())

            valid_categories = list(self.CATEGORIES.keys()) + ["general"]
            if category in valid_categories:
                logger.debug(
                    f"IA clasifico como '{category}': {article.get('title', '')[:50]}"
                )
                return category

            return "general"

        except Exception as e:
            logger.error(f"Error en clasificacion IA: {e}")
            return self.classify(article)

    def classify_batch(self, news: list[dict]) -> list[dict]:
        """Clasifica una lista de noticias."""

        for article in news:
            article["category"] = self.classify(article)

        return news

    def _normalize(self, text: object) -> str:
        normalized = unicodedata.normalize("NFD", str(text).lower())
        return "".join(
            char for char in normalized if unicodedata.category(char) != "Mn"
        )
