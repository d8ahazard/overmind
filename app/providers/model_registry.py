import asyncio
from typing import Any, Dict, List

from app.providers.base import ModelInfo, ProviderBase, ProviderError
from app.providers.openai_provider import OpenAIProvider
from app.providers.anthropic_provider import AnthropicProvider
from app.providers.groq_provider import GroqProvider
from app.providers.gemini_provider import GeminiProvider


class ModelRegistry:
    def __init__(self) -> None:
        self._providers: Dict[str, ProviderBase] = {
            "openai": OpenAIProvider(),
            "anthropic": AnthropicProvider(),
            "groq": GroqProvider(),
            "gemini": GeminiProvider(),
        }
        self._cache: Dict[str, List[ModelInfo]] = {}
        self._lock = asyncio.Lock()

    def providers(self) -> List[str]:
        return list(self._providers.keys())

    async def refresh(self, provider: str) -> List[ModelInfo]:
        if provider not in self._providers:
            raise ProviderError(f"Unknown provider: {provider}")
        async with self._lock:
            models = await self._providers[provider].list_models()
            self._cache[provider] = models
        return models

    async def list_models(self, provider: str | None = None, enabled: List[str] | None = None) -> List[ModelInfo]:
        if provider:
            if provider not in self._providers:
                raise ProviderError(f"Unknown provider: {provider}")
            if enabled is not None and provider not in enabled:
                return []
            if provider not in self._cache:
                await self.refresh(provider)
            return self._cache.get(provider, [])

        all_models: List[ModelInfo] = []
        for name in self._providers:
            if enabled is not None and name not in enabled:
                continue
            if name not in self._cache:
                await self.refresh(name)
            all_models.extend(self._cache.get(name, []))
        return all_models

    async def invoke(self, provider: str, model: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if provider not in self._providers:
            raise ProviderError(f"Unknown provider: {provider}")
        return await self._providers[provider].invoke_model(model, payload)

    async def get_balance(self, provider: str) -> float | None:
        if provider not in self._providers:
            raise ProviderError(f"Unknown provider: {provider}")
        return await self._providers[provider].get_balance()
