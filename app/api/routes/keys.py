from fastapi import APIRouter, HTTPException, Request
from sqlmodel import select

from app.core.crypto import decrypt_value, encrypt_value
from app.db.models import ProviderKey
from app.db.session import get_session

router = APIRouter()


@router.get("/")
def list_keys(request: Request) -> list[dict]:
    master_key = request.app.state.settings.encryption_key
    with get_session() as session:
        keys = list(session.exec(select(ProviderKey)))
    results = []
    for item in keys:
        value = None
        if master_key:
            try:
                value = decrypt_value(item.encrypted_key, master_key)
            except Exception:
                value = None
        results.append({"id": item.id, "provider": item.provider, "has_key": value is not None})
    return results


@router.post("/")
def upsert_key(payload: dict, request: Request) -> dict:
    provider = payload.get("provider")
    value = payload.get("key")
    master_key = request.app.state.settings.encryption_key
    if not provider or not value:
        raise HTTPException(status_code=400, detail="provider and key required")
    if not master_key:
        raise HTTPException(status_code=400, detail="AI_DEVTEAM_MASTER_KEY not set")

    encrypted = encrypt_value(value, master_key)
    with get_session() as session:
        existing = session.exec(select(ProviderKey).where(ProviderKey.provider == provider)).first()
        if existing:
            existing.encrypted_key = encrypted
            session.add(existing)
        else:
            session.add(ProviderKey(provider=provider, encrypted_key=encrypted))
        session.commit()
    return {"status": "ok", "provider": provider}


@router.post("/token")
def issue_token(payload: dict, request: Request) -> dict:
    provider = payload.get("provider")
    ttl_seconds = int(payload.get("ttl_seconds", 900))
    if not provider:
        raise HTTPException(status_code=400, detail="provider required")
    broker = request.app.state.secrets_broker
    token = broker.issue_provider_token(provider, ttl_seconds=ttl_seconds)
    if not token:
        raise HTTPException(status_code=404, detail="key not found or broker unavailable")
    return {
        "provider": token.provider,
        "token": token.token,
        "expires_at": token.expires_at.isoformat(),
    }


@router.delete("/{provider}")
def delete_key(provider: str) -> dict:
    with get_session() as session:
        existing = session.exec(select(ProviderKey).where(ProviderKey.provider == provider)).first()
        if not existing:
            raise HTTPException(status_code=404, detail="Key not found")
        session.delete(existing)
        session.commit()
    return {"status": "deleted", "provider": provider}
