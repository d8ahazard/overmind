from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


class ProviderError(Exception):
    pass


@dataclass
class ModelInfo:
    id: str
    provider: str
    supports_tools: bool = False
    supports_vision: bool = False
    context_length: int = 0
    recommended_roles: List[str] | None = None


class ProviderBase:
    name: str = ""

    def validate_key(self) -> bool:
        raise NotImplementedError

    async def get_balance(self) -> float | None:
        return None

    async def list_models(self, api_key: str | None = None) -> List[ModelInfo]:
        raise NotImplementedError

    async def invoke_model(
        self, model: str, payload: Dict[str, Any], api_key: str | None = None
    ) -> Dict[str, Any]:
        raise NotImplementedError
