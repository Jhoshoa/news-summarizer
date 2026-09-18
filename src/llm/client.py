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
        "kimi": {
            # Moonshot AI's international platform (api.moonshot.ai, not the
            # .cn domestic one) -- OpenAI-compatible. Paid tier (Tier1, bought
            # 2026-09), used as the last resort on purpose: it's the only
            # provider here that costs real money per call, so it should only
            # fire once every free provider (groq/gemini/nvidia) already
            # failed, not compete with them for everyday traffic.
            #
            # kimi-latest, kimi-k2-*, and every moonshot-v1-* name are
            # discontinued as of 2026-09 (confirmed against Moonshot's live
            # docs, not from training-data memory) -- kimi-k2.6 is the
            # current general-purpose model, used for all three tiers since
            # this provider only exists as a fallback, not to fine-tune for
            # speed vs quality.
            "base_url": "https://api.moonshot.ai/v1",
            "models": {
                "fast": "kimi-k2.6",
                "balanced": "kimi-k2.6",
                "quality": "kimi-k2.6",
            },
        },
    }

    def __init__(
        self,
        provider: str = "groq",
        api_key: str = None,
        models: dict[str, str] | None = None,
        base_url: str | None = None,
        timeout: float = 45.0,
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

        # timeout explicito + max_retries=1: el SDK de OpenAI por defecto usa
        # 600s de timeout y reintenta 2 veces por su cuenta, lo que puede
        # dejar una sola llamada colgada mas de 20 minutos antes de fallar y
        # dejarle el turno al siguiente proveedor del LLMRouter. Con esto,
        # un proveedor lento/caido se descarta rapido en vez de trabar todo
        # el pipeline (visto en vivo: /trigger/summary colgado ~11 min en
        # un solo provider tras el fallback de Gemini).
        #
        # kimi es la unica excepcion: incluso con "thinking" desactivado
        # (ver chat()), el tiempo de respuesta escala con el tamano del lote
        # -- confirmado en vivo, un lote de 8 noticias (el maximo real de
        # SUMMARY_CANDIDATES_EXTENDED_LIMIT) tardo 63.6s de punta a punta,
        # por encima de los 45s compartidos con el resto de proveedores. Como
        # kimi es siempre el ultimo del LLMRouter (no hay a quien pasarle la
        # posta despues), no tiene sentido cortarlo temprano como a los
        # gratuitos: se le da mas margen en vez de fallar una categoria
        # entera por un timeout evitable.
        effective_timeout = 120.0 if provider == "kimi" else timeout
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=resolved_base_url,
            timeout=effective_timeout,
            max_retries=1,
        )
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

        # kimi-k2.6 es un modelo "thinking" por defecto: gasta parte del
        # presupuesto de max_tokens en un razonamiento interno
        # (reasoning_content) que nunca se ve en la respuesta -- confirmado en
        # vivo, con thinking habilitado una llamada real de resumen (quality,
        # batch de 2 noticias) tardo mas de 90s y termino en timeout, y una
        # clasificacion simple tardo entre 33 y 89s por el mismo motivo.
        # Se desactiva "thinking" explicitamente (extra_body) en vez de darle
        # presupuesto extra: confirmado en vivo que sin thinking la misma
        # llamada baja de ~90s a ~2s y no gasta tokens en razonamiento oculto.
        # Con thinking desactivado el modelo tambien exige otro temperature
        # fijo -- confirmado en vivo: 400 "invalid temperature: only 0.6 is
        # allowed for this model" (era 1 con thinking habilitado, asi que el
        # valor fijo depende del modo, no es una preferencia arbitraria).
        effective_temperature = temperature
        effective_max_tokens = max_tokens
        extra_body = None
        if self.provider == "kimi":
            effective_temperature = 0.6
            extra_body = {"thinking": {"type": "disabled"}}

        try:
            response = await self._client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=effective_temperature,
                max_tokens=effective_max_tokens,
                extra_body=extra_body,
            )

            content = response.choices[0].message.content
            logger.debug(f"LLM response: {content[:100]}...")
            return content

        except Exception as e:
            logger.error(f"Error en LLM chat: {e}")
            raise

    async def close(self):
        """Cierra el cliente."""
        await self._client.close()
        logger.info("LLMProvider cerrado")

    def __repr__(self) -> str:
        return f"LLMProvider(provider={self.provider}, model={self.models['quality']})"
