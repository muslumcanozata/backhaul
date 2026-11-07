from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import AppState, get_current_user, get_db, get_state
from app.models import User
from app.schemas import LoginRequest, TokenResponse, UserOut
from app.security import create_token, verify_password
from app.supabase_client import SupabaseError, sign_in

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, state: AppState = Depends(get_state), db: Session = Depends(get_db)) -> TokenResponse:
    email = str(body.email)
    if state.settings.supabase_enabled:
        try:
            token, auth_id = sign_in(state.settings, email, body.password)
        except SupabaseError as exc:
            raise HTTPException(status_code=401, detail="E-posta veya parola hatalı") from exc
        user = db.get(User, auth_id) or db.query(User).filter(User.email == email).one_or_none()
        if user is None or not user.active:
            raise HTTPException(status_code=401, detail="E-posta veya parola hatalı")
        if user.id != auth_id:
            raise HTTPException(status_code=401, detail="Kullanıcı kimliği eşleşmiyor; yeniden oluşturun")
    else:
        user = db.query(User).filter(User.email == email).one_or_none()
        if user is None or not user.active or not verify_password(body.password, user.password_hash):
            raise HTTPException(status_code=401, detail="E-posta veya parola hatalı")
        token = create_token(state.settings, user.id, user.tenant_id, user.role)

    if state.settings.deployment_mode == "dedicated" and user.role != "platform_admin":
        if user.tenant_id != UUID(state.settings.tenant_id or ""):
            raise HTTPException(status_code=403, detail="Bu pod başka firmayı kabul etmez")
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return UserOut(id=user.id, email=user.email, role=user.role, tenant_id=user.tenant_id)
