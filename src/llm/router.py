from __future__ import annotations

from contextlib import suppress

import openai
from loguru import logger

from .client import LLMProvider


class LLMRouter:
    """Enrrutador que prueba multiples LLM providers en orden ante errores de rate limit."""

    def __init__(
        self,
        providers: list[dict],
        models: dict[str, str] | None = None,
        timeout: float = 45.0,
    ):
        self._providers: list[LLMProvider] = []
        self._active_index = 0

        for cfg in providers:
            provider_name: str = cfg["provider"]
            api_key: str | None = cfg.get("api_key")
            base_url: str | None = cfg.get("base_url")
            if not api_key:
                logger.warning(
                    f"API key vacia para provider={provider_name}, saltando"
                )
                continue
            try:
                p = LLMProvider(
                    provider=provider_name,
                    api_key=api_key,
                    models=models,
                    base_url=base_url,
                    timeout=timeout,
                )
                self._providers.append(p)
            except Exception as e:
                logger.warning(f"Error inicializando provider {provider_name}: {e}")

        if not self._providers:
            raise ValueError("No hay providers disponibles")

        logger.info(
            f"LLMRouter inicializado con {len(self._providers)} providers: "
            f"{[p.provider for p in self._providers]}"
        )

    @property
    def active_provider(self) -> str:
        return self._providers[self._active_index].provider

    @property
    def provider(self) -> str:
        """Compatibilidad con codigo que accede self.llm.provider."""
        return self.active_provider

    @property
    def models(self) -> dict[str, str]:
        """Compatibilidad con codigo que accede self.llm.models."""
        return self._providers[self._active_index].models  # type: ignore[no-any-return]

    def reset(self):
        """Reinicia al primer provider al inicio de cada ciclo."""
        self._active_index = 0
        logger.info(f"LLMRouter reseteado al provider inicial: {self.active_provider}")

    async def chat(
        self,
        prompt: str,
        quality: str = "balanced",
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4000,
    ) -> str:
        """Envia un prompt probando cada provider en orden si hay rate limit."""
        last_error: BaseException | None = None
        start_index = self._active_index

        for attempt in range(len(self._providers)):
            idx = (start_index + attempt) % len(self._providers)
            provider = self._providers[idx]
            try:
                result = await provider.chat(
                    prompt,
                    quality=quality,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                self._active_index = idx
                return result
            except openai.RateLimitError as e:
                logger.warning(
                    f"Rate limit en provider={provider.provider}, "
                    f"cambiando al siguiente..."
                )
                last_error = e
            except Exception as e:
                logger.error(
                    f"Error en provider={provider.provider}: {e}"
                )
                last_error = e

        if last_error is not None:
            raise last_error
        raise RuntimeError("No se pudo completar la operacion con ningun provider")

    async def chat_batch(
        self,
        prompts: list[str],
        quality: str = "balanced",
        system_prompt: str | None = None,
        temperature: float = 0.3,
    ) -> list[str]:
        """Ejecuta un batch completo, con failover al siguiente provider si falla."""
        last_error: BaseException | None = None
        start_index = self._active_index

        for attempt in range(len(self._providers)):
            idx = (start_index + attempt) % len(self._providers)
            provider = self._providers[idx]
            try:
                result = await provider.chat_batch(
                    prompts,
                    quality=quality,
                    system_prompt=system_prompt,
                    temperature=temperature,
                )
                self._active_index = idx
                return result
            except openai.RateLimitError as e:
                logger.warning(
                    f"Rate limit en batch provider={provider.provider}, "
                    f"failover al siguiente..."
                )
                last_error = e
            except Exception as e:
                logger.error(f"Error en batch provider={provider.provider}: {e}")
                last_error = e

        if last_error is not None:
            raise last_error
        raise RuntimeError("No se pudo completar el batch con ningun provider")

    async def close(self):
        for p in self._providers:
            with suppress(Exception):
                await p.close()

    def __repr__(self) -> str:
        return (
            f"LLMRouter(active={self._providers[self._active_index].provider}, "
            f"providers={[p.provider for p in self._providers]})"
        )
