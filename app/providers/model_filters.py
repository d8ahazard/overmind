from typing import Iterable, List


_BLOCKED_TOKENS = [
    "audio",
    "tts",
    "embedding",
    "moderation",
    "realtime",
    "transcribe",
    "whisper",
    "sora",
]
_IMAGE_TOKENS = ["image", "dall-e"]


def is_image_model(model_id: str) -> bool:
    name = model_id.lower()
    return any(token in name for token in _IMAGE_TOKENS)


def is_code_model(model_id: str) -> bool:
    name = model_id.lower()
    return "codex" in name or "code" in name


def is_chat_model(provider: str, model_id: str) -> bool:
    name = model_id.lower()
    if any(token in name for token in _BLOCKED_TOKENS) or is_image_model(model_id):
        return False
    if provider == "openai":
        if any(token in name for token in ["instruct", "davinci", "babbage", "ada", "codex"]):
            return False
        return (
            name.startswith("gpt-")
            or name.startswith("chatgpt-")
            or name.startswith("o1")
            or name.startswith("o3")
            or name.startswith("o4")
        )
    if provider == "anthropic":
        return "claude" in name
    if provider == "gemini":
        return "gemini" in name
    # Groq and most other providers expose chat-first models on the chat endpoint.
    return True


def filter_chat_models(provider: str, models: Iterable[str]) -> List[str]:
    return [model_id for model_id in models if is_chat_model(provider, model_id)]


def pick_best_chat_model(models: Iterable[str]) -> str | None:
    return _pick_by_priority(models, ["max", "pro", "o3", "o1", "gpt-5", "gpt-4.1", "gpt-4o", "gpt-4"])


def pick_worker_chat_model(models: Iterable[str]) -> str | None:
    return _pick_by_priority(
        models, ["mini", "nano", "o4-mini", "gpt-4o-mini", "gpt-4.1-mini", "gpt-4o"]
    )


def pick_code_chat_model(models: Iterable[str]) -> str | None:
    return _pick_by_priority(models, ["codex", "code", "gpt-5", "gpt-4.1", "gpt-4o", "gpt-4"])


def pick_image_model(models: Iterable[str]) -> str | None:
    return _pick_by_priority(models, ["image", "dall-e-3", "dall-e-2"])


def _pick_by_priority(models: Iterable[str], priority: List[str]) -> str | None:
    items = [item for item in models if item]
    if not items:
        return None
    for tag in priority:
        match = next((m for m in items if tag in m.lower()), None)
        if match:
            return match
    return items[0]
