import os
from typing import Any, Dict, List

import httpx

from app.providers.base import ModelInfo, ProviderBase, ProviderError


class AnthropicProvider(ProviderBase):
    name = "anthropic"

    def __init__(self) -> None:
        self.api_key = os.getenv("ANTHROPIC_API_KEY")

    def validate_key(self) -> bool:
        return bool(self.api_key)

    async def list_models(self) -> List[ModelInfo]:
        if not self.api_key:
            return []
        # Anthropic does not provide a stable public model list API.
        return []

    async def invoke_model(self, model: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.api_key:
            raise ProviderError("ANTHROPIC_API_KEY not set")
        prompt = payload.get("prompt", "")
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        body = {"model": model, "max_tokens": 512, "messages": [{"role": "user", "content": prompt}]}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=body)
            if response.status_code != 200:
                raise ProviderError(f"Anthropic invoke failed: {response.text}")
            data = response.json()
        content_blocks = data.get("content", [])
        content = content_blocks[0].get("text", "") if content_blocks else ""
        return {"content": content}
