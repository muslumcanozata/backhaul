from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.accounts import STAFF_ROLES, create_tenant_user, update_tenant_user
from app.deps import get_current_user, get_db
from app.models import User
from app.schemas import UserAccessPatch, UserCreate, UserOut

router = APIRouter(tags=["users"])


def _tenant_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "tenant_admin" or user.tenant_id is None:
        raise HTTPException(status_code=403, detail="Kullanıcıları firma yöneticisi yönetir")
    return user


@router.get("/users", response_model=list[UserOut])
def list_users(user: User = Depends(_tenant_admin), db: Session = Depends(get_db)) -> list[User]:
    return db.query(User).filter(User.tenant_id == user.tenant_id).order_by(User.email).all()


@router.post("/users", response_model=UserOut)
def create_user(body: UserCreate, user: User = Depends(_tenant_admin), db: Session = Depends(get_db)) -> User:
    if body.role not in STAFF_ROLES:
        raise HTTPException(status_code=422, detail="Firma yöneticisi operasyoncu veya izleyici açar")
    return create_tenant_user(db, user.tenant_id, str(body.email), body.password, body.role)


@router.patch("/users/{user_id}", response_model=UserOut)
def patch_user(
    user_id: UUID,
    body: UserAccessPatch,
    actor: User = Depends(_tenant_admin),
    db: Session = Depends(get_db),
) -> User:
    target = db.get(User, user_id)
    if target is None or target.tenant_id != actor.tenant_id:
        raise HTTPException(status_code=404, detail="Kullanıcı yok")
    return update_tenant_user(db, actor, target, body.role, body.active, allow_admin_role=False)
