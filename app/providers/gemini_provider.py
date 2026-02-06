import os
from typing import Any, Dict, List

import httpx

from app.providers.base import ModelInfo, ProviderBase, ProviderError


class GeminiProvider(ProviderBase):
    name = "gemini"

    def __init__(self) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY")

    def validate_key(self) -> bool:
        return bool(self.api_key)

    async def list_models(self) -> List[ModelInfo]:
        if not self.api_key:
            return []
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                "https://generativelanguage.googleapis.com/v1beta/models",
                params={"key": self.api_key},
            )
            if response.status_code != 200:
                raise ProviderError(f"Gemini list_models failed: {response.text}")
            data = response.json().get("models", [])
        return [ModelInfo(id=item["name"], provider=self.name) for item in data]

    async def invoke_model(
        self, model: str, payload: Dict[str, Any], api_key: str | None = None
    ) -> Dict[str, Any]:
        key = api_key or self.api_key
        if not key:
            raise ProviderError("GEMINI_API_KEY not set")
        prompt = payload.get("prompt", "")
        body = {"contents": [{"parts": [{"text": prompt}]}]}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent",
                params={"key": key},
                json=body,
            )
            if response.status_code != 200:
                raise ProviderError(f"Gemini invoke failed: {response.text}")
            data = response.json()
        candidates = data.get("candidates", [])
        content = ""
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                content = parts[0].get("text", "")
        return {"content": content}
