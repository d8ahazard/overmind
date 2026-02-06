import asyncio
import inspect
from typing import Any, Dict, List

from app.providers.base import ModelInfo, ProviderBase, ProviderError
from app.core.secrets import SecretsBroker
from app.providers.openai_provider import OpenAIProvider
from app.providers.anthropic_provider import AnthropicProvider
from app.providers.groq_provider import GroqProvider
from app.providers.gemini_provider import GeminiProvider


class ModelRegistry:
    def __init__(self, secrets_broker: SecretsBroker | None = None) -> None:
        self._providers: Dict[str, ProviderBase] = {
            "openai": OpenAIProvider(),
            "anthropic": AnthropicProvider(),
            "groq": GroqProvider(),
            "gemini": GeminiProvider(),
        }
        self._cache: Dict[str, List[ModelInfo]] = {}
        self._lock = asyncio.Lock()
        self._secrets_broker = secrets_broker

    def providers(self) -> List[str]:
        return list(self._providers.keys())

    async def refresh(self, provider: str) -> List[ModelInfo]:
        if provider not in self._providers:
            raise ProviderError(f"Unknown provider: {provider}")
        api_key = self._secrets_broker.get_provider_key(provider) if self._secrets_broker else None
        async with self._lock:
            provider_impl = self._providers[provider]
            if "api_key" in inspect.signature(provider_impl.list_models).parameters:
                models = await provider_impl.list_models(api_key=api_key)
            else:
                original_key = getattr(provider_impl, "api_key", None)
                if api_key and not original_key:
                    setattr(provider_impl, "api_key", api_key)
                models = await provider_impl.list_models()
                if api_key and not original_key:
                    setattr(provider_impl, "api_key", original_key)
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
            elif not self._cache.get(provider) and self._secrets_broker:
                if self._secrets_broker.get_provider_key(provider):
                    await self.refresh(provider)
            return self._cache.get(provider, [])

        all_models: List[ModelInfo] = []
        for name in self._providers:
            if enabled is not None and name not in enabled:
                continue
            if name not in self._cache:
                await self.refresh(name)
            elif not self._cache.get(name) and self._secrets_broker:
                if self._secrets_broker.get_provider_key(name):
                    await self.refresh(name)
            all_models.extend(self._cache.get(name, []))
        return all_models

    async def invoke(self, provider: str, model: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if provider not in self._providers:
            raise ProviderError(f"Unknown provider: {provider}")
        provider_token = payload.pop("provider_token", None)
        api_key = None
        if provider_token and self._secrets_broker:
            api_key = self._secrets_broker.resolve_token(provider_token)
        return await self._providers[provider].invoke_model(model, payload, api_key=api_key)

    async def suggest_manager_model(self, provider: str) -> str | None:
        models = await self.list_models(provider, enabled=[provider])
        if not models:
            return None
        ordered = sorted((m.id for m in models), key=_manager_model_rank, reverse=True)
        return ordered[0] if ordered else None


def _manager_model_rank(model_id: str) -> int:
    name = model_id.lower()
    if "max" in name:
        return 100
    if "o1" in name:
        return 95
    if "gpt-4" in name:
        return 90
    if "claude-3.5" in name or "claude-3-5" in name:
        return 85
    if "sonnet" in name:
        return 80
    if "pro" in name:
        return 75
    return 10

    async def get_balance(self, provider: str) -> float | None:
        if provider not in self._providers:
            raise ProviderError(f"Unknown provider: {provider}")
        return await self._providers[provider].get_balance()
