from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.accounts import TENANT_ROLES, create_tenant_user, update_tenant_user
from app.deps import AppState, get_current_user, get_db, get_state
from app.models import Tenant, TenantSettings, User
from app.schemas import TenantCreate, TenantOut, UserAccessPatch, UserCreate, UserOut

router = APIRouter(prefix="/tenants", tags=["tenants"])


def _platform(user: User = Depends(get_current_user)) -> User:
    if user.role != "platform_admin":
        raise HTTPException(status_code=403, detail="Platform yöneticisi gerekli")
    return user


@router.post("", response_model=TenantOut)
def create_tenant(
    body: TenantCreate,
    state: AppState = Depends(get_state),
    db: Session = Depends(get_db),
    _: User = Depends(_platform),
) -> Tenant:
    if state.settings.deployment_mode == "dedicated":
        raise HTTPException(status_code=403, detail="Ayrı pod yeni firma açmaz")
    if db.query(Tenant).filter(Tenant.code == body.code).one_or_none():
        raise HTTPException(status_code=409, detail="Firma kodu kullanılıyor")
    tenant = Tenant(name=body.name, code=body.code)
    db.add(tenant)
    db.flush()
    db.add(TenantSettings(tenant_id=tenant.id, enabled_trailer_types=["tenteli"]))
    db.commit()
    db.refresh(tenant)
    return tenant


@router.get("", response_model=list[TenantOut])
def list_tenants(db: Session = Depends(get_db), _: User = Depends(_platform)) -> list[Tenant]:
    return db.query(Tenant).order_by(Tenant.name).all()


@router.post("/{tenant_id}/users", response_model=UserOut)
def create_user(
    tenant_id: str,
    body: UserCreate,
    state: AppState = Depends(get_state),
    db: Session = Depends(get_db),
    _: User = Depends(_platform),
) -> User:
    from uuid import UUID

    if body.role not in TENANT_ROLES:
        raise HTTPException(status_code=422, detail="Rol tenant_admin, dispatcher veya viewer olmalı")
    try:
        parsed = UUID(tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Firma yok") from exc
    if state.settings.deployment_mode == "dedicated" and parsed != UUID(state.settings.tenant_id or ""):
        raise HTTPException(status_code=403, detail="Bu pod başka firmayı kabul etmez")
    tenant = db.get(Tenant, parsed)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Firma yok")
    return create_tenant_user(db, tenant.id, str(body.email), body.password, body.role)


@router.get("/{tenant_id}/users", response_model=list[UserOut])
def list_users(tenant_id: str, db: Session = Depends(get_db), _: User = Depends(_platform)) -> list[User]:
    from uuid import UUID

    try:
        parsed = UUID(tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Firma yok") from exc
    if db.get(Tenant, parsed) is None:
        raise HTTPException(status_code=404, detail="Firma yok")
    return db.query(User).filter(User.tenant_id == parsed).order_by(User.email).all()


@router.patch("/{tenant_id}/users/{user_id}", response_model=UserOut)
def patch_user(
    tenant_id: str,
    user_id: str,
    body: UserAccessPatch,
    db: Session = Depends(get_db),
    actor: User = Depends(_platform),
) -> User:
    from uuid import UUID

    try:
        parsed_tenant = UUID(tenant_id)
        parsed_user = UUID(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Kullanıcı yok") from exc
    target = db.get(User, parsed_user)
    if target is None or target.tenant_id != parsed_tenant:
        raise HTTPException(status_code=404, detail="Kullanıcı yok")
    return update_tenant_user(db, actor, target, body.role, body.active, allow_admin_role=True)
