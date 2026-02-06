import os
from typing import Any, Dict, List

import httpx

from app.providers.base import ModelInfo, ProviderBase, ProviderError


class OpenAIProvider(ProviderBase):
    name = "openai"

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY")

    def validate_key(self) -> bool:
        return bool(self.api_key)

    async def list_models(self, api_key: str | None = None) -> List[ModelInfo]:
        key = api_key or self.api_key
        if not key:
            return []
        headers = {"Authorization": f"Bearer {key}"}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get("https://api.openai.com/v1/models", headers=headers)
            if response.status_code != 200:
                raise ProviderError(f"OpenAI list_models failed: {response.text}")
            data = response.json().get("data", [])
        return [ModelInfo(id=item["id"], provider=self.name) for item in data]

    async def invoke_model(
        self, model: str, payload: Dict[str, Any], api_key: str | None = None
    ) -> Dict[str, Any]:
        key = api_key or self.api_key
        if not key:
            raise ProviderError("OPENAI_API_KEY not set")
        prompt = payload.get("prompt", "")
        headers = {"Authorization": f"Bearer {key}"}
        chat_body = {"model": model, "messages": [{"role": "user", "content": prompt}]}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=chat_body,
            )
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return {"content": content}
            error_text = response.text
            # Some OpenAI models are only supported on the Responses API.
            if "v1/responses" not in error_text:
                raise ProviderError(f"OpenAI invoke failed: {error_text}")
            response = await client.post(
                "https://api.openai.com/v1/responses",
                headers=headers,
                json={"model": model, "input": prompt},
            )
            if response.status_code != 200:
                raise ProviderError(f"OpenAI invoke failed: {response.text}")
            data = response.json()
        content = _extract_response_text(data)
        return {"content": content}


def _extract_response_text(data: Dict[str, Any]) -> str:
    if isinstance(data, dict):
        direct = data.get("output_text")
        if isinstance(direct, str):
            return direct
        output = data.get("output")
        if isinstance(output, list):
            chunks: List[str] = []
            for item in output:
                content = item.get("content") if isinstance(item, dict) else None
                if isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "output_text":
                            text = part.get("text")
                            if isinstance(text, str):
                                chunks.append(text)
            if chunks:
                return "\n".join(chunks)
    return ""
