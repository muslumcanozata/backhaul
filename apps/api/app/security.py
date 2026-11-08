from datetime import UTC, datetime, timedelta
from functools import lru_cache
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


@lru_cache
def _jwks_client(supabase_url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json")


def decode_token(settings: Settings, token: str) -> dict:
    options = {"require": ["exp", "sub"]}
    algorithm = jwt.get_unverified_header(token).get("alg")
    issuer = f"{settings.supabase_url.rstrip('/')}/auth/v1" if settings.supabase_enabled and settings.supabase_url else None
    if settings.supabase_enabled and algorithm in {"ES256", "RS256"}:
        key = _jwks_client(settings.supabase_url).get_signing_key_from_jwt(token).key
        return jwt.decode(
            token,
            key,
            algorithms=[algorithm],
            audience="authenticated",
            issuer=issuer,
            options=options,
        )
    kwargs: dict = {
        "algorithms": ["HS256"],
        "options": options,
    }
    if issuer:
        kwargs["audience"] = "authenticated"
        kwargs["issuer"] = issuer
    return jwt.decode(token, settings.token_secret, **kwargs)
