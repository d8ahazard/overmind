import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from sqlmodel import select

from app.core.crypto import decrypt_value
from app.db.models import ProviderKey
from app.db.session import get_session


@dataclass
class SecretToken:
    token: str
    provider: str
    expires_at: datetime


class SecretsBroker:
    def __init__(self, master_key: str | None) -> None:
        self._master_key = master_key
        self._tokens: dict[str, tuple[str, datetime]] = {}

    def issue_provider_token(self, provider: str, ttl_seconds: int = 900) -> Optional[SecretToken]:
        if not self._master_key:
            return None
        with get_session() as session:
            stored = session.exec(
                select(ProviderKey).where(ProviderKey.provider == provider)
            ).first()
        if not stored:
            return None
        try:
            secret_value = decrypt_value(stored.encrypted_key, self._master_key)
        except Exception:
            return None
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        self._tokens[token] = (secret_value, expires_at)
        return SecretToken(token=token, provider=provider, expires_at=expires_at)

    def resolve_token(self, token: str) -> Optional[str]:
        if not token:
            return None
        value = self._tokens.get(token)
        if not value:
            return None
        secret, expires_at = value
        if datetime.utcnow() > expires_at:
            self._tokens.pop(token, None)
            return None
        return secret
