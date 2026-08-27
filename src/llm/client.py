import asyncio

from loguru import logger
from openai import AsyncOpenAI


class LLMProvider:
    """Cliente unificado para Groq y OpenAI."""

    PROVIDERS = {
        "groq": {
            "base_url": "https://api.groq.com/openai/v1",
            "models": {
                "fast": "openai/gpt-oss-20b",
                "balanced": "qwen/qwen3.6-27b",
                "quality": "openai/gpt-oss-120b",
            },
        },
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "models": {
                "fast": "gpt-4o-mini",
                "balanced": "gpt-4o",
                "quality": "gpt-4o",
            },
        },
        "github": {
            "base_url": "https://models.github.ai/inference",
            "models": {
                "fast": "openai/gpt-4.1-mini",
                "balanced": "openai/gpt-4.1-mini",
                "quality": "openai/gpt-4.1-mini",
            },
        },
        "gemini": {
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
            "models": {
                # gemini-2.5-* fue retirado para cuentas nuevas (confirmado con
                # un 404 real en 2026-08-27: "no longer available to new
                # users, use gemini-3.5-flash-lite"). flash-lite es mas debil
                # pero tiene mas cuota diaria gratis, asi que se usa para
                # clasificacion/dedup, tareas simples de si/no donde el
                # volumen importa mas que la calidad.
                "fast": "gemini-3.5-flash-lite",
                "balanced": "gemini-3.5-flash-lite",
                # flash tiene mejor calidad para el resumen final; como
                # fallback (no como principal) la cuota gratis alcanza de sobra.
                "quality": "gemini-3.6-flash",
            },
        },
        "nvidia": {
            "base_url": "https://integrate.api.nvidia.com/v1",
            "models": {
                # mistral-small-4-119b-2603 reached end-of-life on NVIDIA's
                # platform (2026-07-27, confirmed via a live 410 response).
                # mistral-nemotron verified reachable on the free-tier key.
                "fast": "mistralai/mistral-nemotron",
                "balanced": "mistralai/mistral-nemotron",
                "quality": "mistralai/mistral-nemotron",
            },
        },
    }

    def __init__(
        self,
        provider: str = "groq",
        api_key: str = None,
        models: dict[str, str] | None = None,
        base_url: str | None = None,
    ):
        if provider not in self.PROVIDERS:
            raise ValueError(
                f"Provider {provider} no soportado. Providers disponibles: {list(self.PROVIDERS.keys())}"
            )

        if not api_key:
            raise ValueError(f"API key requerida para el provider {provider}")

        self.provider = provider
        config = self.PROVIDERS[provider]
        resolved_base_url = base_url or config["base_url"]

        self._client = AsyncOpenAI(api_key=api_key, base_url=resolved_base_url)
        self.models = config["models"].copy()
        if models:
            self.models.update(models)
        logger.info(
            f"LLMProvider inicializado con provider={provider}, "
            f"base_url={resolved_base_url}, "
            f"models={self.models}"
        )

    async def chat(
        self,
        prompt: str,
        quality: str = "balanced",
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4000,
    ) -> str:
        """Envía un prompt y retorna la respuesta."""

        model = self.models[quality]

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await self._client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            content = response.choices[0].message.content
            logger.debug(f"LLM response: {content[:100]}...")
            return content

        except Exception as e:
            logger.error(f"Error en LLM chat: {e}")
            raise

    async def chat_batch(
        self,
        prompts: list[str],
        quality: str = "balanced",
        system_prompt: str | None = None,
        temperature: float = 0.3,
    ) -> list[str]:
        """Múltiples prompts en paralelo."""

        tasks = [self.chat(p, quality, system_prompt, temperature) for p in prompts]
        return await asyncio.gather(*tasks)

    async def close(self):
        """Cierra el cliente."""
        await self._client.close()
        logger.info("LLMProvider cerrado")

    def __repr__(self) -> str:
        return f"LLMProvider(provider={self.provider}, model={self.models['quality']})"
