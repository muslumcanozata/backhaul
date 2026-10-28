from collections.abc import Generator
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings
from app.models import User
from app.security import decode_token

bearer = HTTPBearer(auto_error=False)


class AppState:
    def __init__(self, settings: Settings, factory: sessionmaker[Session]) -> None:
        self.settings = settings
        self.factory = factory


def get_state() -> AppState:
    raise RuntimeError("Uygulama durumu bağlanmadı")


def get_db(state: AppState = Depends(get_state)) -> Generator[Session, None, None]:
    db = state.factory()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    state: AppState = Depends(get_state),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Oturum gerekli")
    try:
        payload = decode_token(state.settings, credentials.credentials)
        user_id = UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Oturum geçersiz") from exc
    user = db.get(User, user_id)
    if user is None or not user.active:
        raise HTTPException(status_code=401, detail="Kullanıcı kapalı")
    if state.settings.deployment_mode == "dedicated":
        expected = UUID(state.settings.tenant_id or "")
        if user.role != "platform_admin" and user.tenant_id != expected:
            raise HTTPException(status_code=403, detail="Bu pod başka firmayı kabul etmez")
    return user


def require_operation_tenant(
    user: User = Depends(get_current_user),
    state: AppState = Depends(get_state),
) -> UUID:
    if user.role == "platform_admin" or user.tenant_id is None:
        raise HTTPException(status_code=403, detail="Platform yöneticisi operasyon verisini açamaz")
    if state.settings.deployment_mode == "dedicated":
        expected = UUID(state.settings.tenant_id or "")
        if user.tenant_id != expected:
            raise HTTPException(status_code=403, detail="Bu pod başka firmayı kabul etmez")
    return user.tenant_id


def require_writer(user: User = Depends(get_current_user)) -> User:
    if user.role not in {"tenant_admin", "dispatcher"}:
        raise HTTPException(status_code=403, detail="Bu işlem için yetki yok")
    return user
