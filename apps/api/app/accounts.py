from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Tenant, User
from app.security import hash_password

TENANT_ROLES = {"tenant_admin", "dispatcher", "viewer"}
STAFF_ROLES = {"dispatcher", "viewer"}


def create_tenant_user(db: Session, tenant_id: UUID, email: str, password: str, role: str) -> User:
    if db.get(Tenant, tenant_id) is None:
        raise HTTPException(status_code=404, detail="Firma yok")
    if db.query(User).filter(User.email == email).one_or_none():
        raise HTTPException(status_code=409, detail="E-posta kullanılıyor")
    user = User(tenant_id=tenant_id, email=email, password_hash=hash_password(password), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_tenant_user(
    db: Session,
    actor: User,
    target: User,
    role: str | None,
    active: bool | None,
    *,
    allow_admin_role: bool,
) -> User:
    if target.tenant_id is None or (actor.tenant_id is not None and target.tenant_id != actor.tenant_id):
        raise HTTPException(status_code=404, detail="Kullanıcı yok")
    if target.id == actor.id:
        raise HTTPException(status_code=403, detail="Kendi erişiminizi kapatamazsınız")
    if target.role == "tenant_admin" and not allow_admin_role:
        raise HTTPException(status_code=403, detail="Firma yöneticisinin erişimini platform yöneticisi değiştirir")
    if role is not None:
        allowed = TENANT_ROLES if allow_admin_role else STAFF_ROLES
        if role not in allowed:
            raise HTTPException(status_code=422, detail="Bu rol atanamaz")
        target.role = role
    if active is not None:
        target.active = active
    db.commit()
    db.refresh(target)
    return target
