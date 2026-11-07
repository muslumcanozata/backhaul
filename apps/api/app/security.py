from datetime import UTC, datetime, timedelta
from uuid import UUID

import bcrypt
import jwt

from app.config import Settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_token(settings: Settings, user_id: UUID, tenant_id: UUID | None, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id) if tenant_id else None,
        "role": role,
        "exp": datetime.now(UTC) + timedelta(minutes=settings.token_ttl_minutes),
    }
    return jwt.encode(payload, settings.token_secret, algorithm="HS256")


def decode_token(settings: Settings, token: str) -> dict:
    options = {"require": ["exp", "sub"]}
    kwargs: dict = {
        "algorithms": ["HS256"],
        "options": options,
    }
    if settings.supabase_enabled:
        kwargs["audience"] = "authenticated"
        kwargs["issuer"] = f"{settings.supabase_url.rstrip('/')}/auth/v1"
    return jwt.decode(token, settings.token_secret, **kwargs)
