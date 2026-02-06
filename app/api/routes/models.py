from typing import List, Optional

from fastapi import APIRouter, Query, Request
from sqlmodel import select

from app.providers.model_registry import ModelRegistry
from app.db.models import ProviderKey
from app.db.session import get_session

router = APIRouter()
registry = ModelRegistry()


@router.get("/", response_model=List[dict])
async def list_models(
    request: Request,
    provider: Optional[str] = Query(default=None),
    only_enabled: bool = Query(default=True),
) -> List[dict]:
    enabled = None
    if only_enabled:
        with get_session() as session:
            enabled = [item.provider for item in session.exec(select(ProviderKey))]
    models = await registry.list_models(provider, enabled=enabled)
    return [model.__dict__ for model in models]


@router.get("/providers", response_model=List[str])
def list_providers() -> List[str]:
    return registry.providers()
