import os
from typing import Any, Dict, List

import httpx

from app.providers.base import ModelInfo, ProviderBase, ProviderError


class GroqProvider(ProviderBase):
    name = "groq"

    def __init__(self) -> None:
        self.api_key = os.getenv("GROQ_API_KEY")

    def validate_key(self) -> bool:
        return bool(self.api_key)

    async def list_models(self, api_key: str | None = None) -> List[ModelInfo]:
        key = api_key or self.api_key
        if not key:
            return []
        headers = {"Authorization": f"Bearer {key}"}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get("https://api.groq.com/openai/v1/models", headers=headers)
            if response.status_code != 200:
                raise ProviderError(f"Groq list_models failed: {response.text}")
            data = response.json().get("data", [])
        return [ModelInfo(id=item["id"], provider=self.name) for item in data]

    async def invoke_model(
        self, model: str, payload: Dict[str, Any], api_key: str | None = None
    ) -> Dict[str, Any]:
        key = api_key or self.api_key
        if not key:
            raise ProviderError("GROQ_API_KEY not set")
        prompt = payload.get("prompt", "")
        headers = {"Authorization": f"Bearer {key}"}
        body = {"model": model, "messages": [{"role": "user", "content": prompt}]}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=body,
            )
            if response.status_code != 200:
                raise ProviderError(f"Groq invoke failed: {response.text}")
            data = response.json()
        content = data["choices"][0]["message"]["content"]
        return {"content": content}
