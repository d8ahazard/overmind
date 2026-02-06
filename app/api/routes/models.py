from typing import Dict, List, Optional

from fastapi import APIRouter, Query, Request
from sqlmodel import select

from app.providers.model_registry import ModelRegistry
from app.db.models import ProviderKey
from app.db.session import get_session

router = APIRouter()


@router.get("/", response_model=List[dict])
async def list_models(
    request: Request,
    provider: Optional[str] = Query(default=None),
    only_enabled: bool = Query(default=True),
) -> List[dict]:
    registry = ModelRegistry(request.app.state.secrets_broker)
    enabled = None
    if only_enabled:
        with get_session() as session:
            enabled = [item.provider for item in session.exec(select(ProviderKey))]
    models = await registry.list_models(provider, enabled=enabled)
    return [model.__dict__ for model in models]


@router.get("/providers", response_model=List[str])
def list_providers() -> List[str]:
    return ModelRegistry().providers()


@router.get("/recommended", response_model=Dict[str, dict])
async def list_recommended(
    request: Request,
    only_enabled: bool = Query(default=True),
) -> Dict[str, dict]:
    registry = ModelRegistry(request.app.state.secrets_broker)
    enabled = None
    if only_enabled:
        with get_session() as session:
            enabled = [item.provider for item in session.exec(select(ProviderKey))]
    models = await registry.list_models(enabled=enabled)
    grouped: Dict[str, List[str]] = {}
    for model in models:
        grouped.setdefault(model.provider, []).append(model.id)
    results: Dict[str, dict] = {}
    for provider, ids in grouped.items():
        filtered = [m for m in ids if _is_text_model(m)]
        code = [m for m in filtered if _is_code_model(m)]
        image = [m for m in ids if _is_image_model(m)]
        results[provider] = {
            "models": {
                "text": filtered,
                "code": code,
                "image": image,
            },
            "defaults": {
                "manager": _pick_best(filtered),
                "worker": _pick_worker(filtered),
                "code": _pick_code(code or filtered),
                "image": _pick_image(image),
            },
        }
    return results


def _is_text_model(model_id: str) -> bool:
    name = model_id.lower()
    blocked = ["audio", "tts", "embedding", "moderation", "realtime", "transcribe", "sora"]
    return not any(item in name for item in blocked) and not _is_image_model(model_id)


def _is_image_model(model_id: str) -> bool:
    name = model_id.lower()
    return "image" in name or "dall-e" in name


def _is_code_model(model_id: str) -> bool:
    name = model_id.lower()
    return "codex" in name or "code" in name


def _pick_best(models: List[str]) -> str | None:
    if not models:
        return None
    priority = ["max", "pro", "o3", "o1", "gpt-5", "gpt-4.1", "gpt-4o", "gpt-4"]
    for tag in priority:
        match = next((m for m in models if tag in m.lower()), None)
        if match:
            return match
    return models[0]


def _pick_worker(models: List[str]) -> str | None:
    if not models:
        return None
    priority = ["mini", "nano", "o4-mini", "gpt-4o-mini", "gpt-4.1-mini", "gpt-4o"]
    for tag in priority:
        match = next((m for m in models if tag in m.lower()), None)
        if match:
            return match
    return models[0]


def _pick_code(models: List[str]) -> str | None:
    if not models:
        return None
    priority = ["codex", "code", "gpt-5", "gpt-4.1", "gpt-4o", "gpt-4"]
    for tag in priority:
        match = next((m for m in models if tag in m.lower()), None)
        if match:
            return match
    return models[0]


def _pick_image(models: List[str]) -> str | None:
    if not models:
        return None
    priority = ["image", "dall-e-3", "dall-e-2"]
    for tag in priority:
        match = next((m for m in models if tag in m.lower()), None)
        if match:
            return match
    return models[0]
