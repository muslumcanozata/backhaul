from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import AppState, get_current_user, get_db, get_state
from app.models import User
from app.schemas import LoginRequest, TokenResponse, UserOut
from app.security import create_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, state: AppState = Depends(get_state), db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == str(body.email)).one_or_none()
    if user is None or not user.active or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="E-posta veya parola hatalı")
    if state.settings.deployment_mode == "dedicated" and user.role != "platform_admin":
        from uuid import UUID

        if user.tenant_id != UUID(state.settings.tenant_id or ""):
            raise HTTPException(status_code=403, detail="Bu pod başka firmayı kabul etmez")
    token = create_token(state.settings, user.id, user.tenant_id, user.role)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return UserOut(id=user.id, email=user.email, role=user.role, tenant_id=user.tenant_id)
