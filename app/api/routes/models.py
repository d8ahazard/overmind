from typing import Dict, List, Optional

from fastapi import APIRouter, Query, Request
from sqlmodel import select

from app.providers.model_registry import ModelRegistry
from app.providers.model_filters import (
    filter_chat_models,
    is_code_model,
    is_image_model,
    pick_best_chat_model,
    pick_code_chat_model,
    pick_image_model,
    pick_worker_chat_model,
)
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
        filtered = filter_chat_models(provider, ids)
        code = [m for m in ids if is_code_model(m)]
        image = [m for m in ids if is_image_model(m)]
        results[provider] = {
            "models": {
                "text": filtered,
                "code": code,
                "image": image,
            },
            "defaults": {
                "manager": pick_best_chat_model(filtered),
                "worker": pick_worker_chat_model(filtered),
                "code": pick_code_chat_model(code or filtered),
                "image": pick_image_model(image),
            },
        }
    return results
