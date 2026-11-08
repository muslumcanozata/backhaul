from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.deps import get_db, require_operation_tenant
from app.models import Driver, TachoSample, TachoState, TenantSettings, Vehicle
from app.schemas import TachoDriverDetailOut, TachoDriverOut, TachoSampleOut
from app.tacho import ensure_sample, limits_from

router = APIRouter(tags=["tacho"])


@router.get("/tacho", response_model=list[TachoDriverOut])
def list_tacho(tenant_id: UUID = Depends(require_operation_tenant), db: Session = Depends(get_db)) -> list[TachoDriverOut]:
    settings = db.get(TenantSettings, tenant_id)
    if settings is None:
        raise HTTPException(status_code=404, detail="Firma ayarı yok")
    drivers = db.query(Driver).filter(Driver.tenant_id == tenant_id).order_by(Driver.name).all()
    driver_ids = [driver.id for driver in drivers]
    states = _states_by_driver(db, driver_ids)
    vehicles = _vehicles_by_driver(db, tenant_id)
    # Liste ekranı örnek zamanına bakmaz; örnek sorgusu detayda kalır.
    return [_row_from(settings, driver, states.get(driver.id), vehicles.get(driver.id), None) for driver in drivers]


@router.get("/tacho/{driver_id}", response_model=TachoDriverDetailOut)
def read_tacho(
    driver_id: UUID,
    tenant_id: UUID = Depends(require_operation_tenant),
    db: Session = Depends(get_db),
) -> TachoDriverDetailOut:
    settings = db.get(TenantSettings, tenant_id)
    driver = db.get(Driver, driver_id)
    if settings is None or driver is None or driver.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Şoför yok")
    state = db.get(TachoState, driver.id)
    if state is not None:
        ensure_sample(db, state)
    vehicle = db.query(Vehicle).filter(Vehicle.driver_id == driver.id).one_or_none()
    samples = (
        db.query(TachoSample)
        .filter(TachoSample.driver_id == driver.id)
        .order_by(TachoSample.recorded_at.desc())
        .limit(200)
        .all()
    )
    db.commit()
    latest = samples[0] if samples else None
    row = _row_from(settings, driver, state, vehicle, latest)
    return TachoDriverDetailOut(
        **row.model_dump(),
        samples=[
            TachoSampleOut(
                recorded_at=item.recorded_at,
                source=item.source,
                continuous_min=item.continuous_min,
                daily_min=item.daily_min,
                weekly_min=item.weekly_min,
                fortnight_min=item.fortnight_min,
                extensions_used=item.extensions_used,
            )
            for item in samples
        ],
    )


def _states_by_driver(db: Session, driver_ids: list[UUID]) -> dict[UUID, TachoState]:
    if not driver_ids:
        return {}
    rows = db.query(TachoState).filter(TachoState.driver_id.in_(driver_ids)).all()
    return {row.driver_id: row for row in rows}


def _vehicles_by_driver(db: Session, tenant_id: UUID) -> dict[UUID, Vehicle]:
    rows = db.query(Vehicle).filter(Vehicle.tenant_id == tenant_id, Vehicle.driver_id.isnot(None)).all()
    return {row.driver_id: row for row in rows if row.driver_id is not None}


def _latest_samples(db: Session, driver_ids: list[UUID]) -> dict[UUID, TachoSample]:
    if not driver_ids:
        return {}
    latest = (
        db.query(TachoSample.driver_id, func.max(TachoSample.recorded_at).label("recorded_at"))
        .filter(TachoSample.driver_id.in_(driver_ids))
        .group_by(TachoSample.driver_id)
        .subquery()
    )
    rows = (
        db.query(TachoSample)
        .join(
            latest,
            and_(
                TachoSample.driver_id == latest.c.driver_id,
                TachoSample.recorded_at == latest.c.recorded_at,
            ),
        )
        .all()
    )
    return {row.driver_id: row for row in rows}


def _row_from(
    settings: TenantSettings,
    driver: Driver,
    state: TachoState | None,
    vehicle: Vehicle | None,
    latest: TachoSample | None,
) -> TachoDriverOut:
    limits = limits_from(settings)
    used_c = state.continuous_min if state else 0
    used_d = state.daily_min if state else 0
    used_w = state.weekly_min if state else 0
    used_f = state.fortnight_min if state else 0
    used_e = state.extensions_used if state else 0
    remain_c = max(0, limits.continuous_min - used_c)
    remain_d = max(0, limits.daily_min - used_d)
    remain_w = max(0, limits.weekly_min - used_w)
    remain_f = max(0, limits.fortnight_min - used_f)
    warning = bool(
        state
        and (
            remain_c <= limits.warning_min
            or remain_d <= limits.warning_min
            or remain_w <= limits.warning_min
            or remain_f <= limits.warning_min
        )
    )
    return TachoDriverOut(
        driver_id=driver.id,
        name=driver.name,
        phone=driver.phone,
        card_id=driver.card_id,
        plate=vehicle.plate if vehicle else None,
        source=state.source if state else None,
        continuous_used=used_c,
        continuous_limit=limits.continuous_min,
        continuous_remain=remain_c,
        daily_used=used_d,
        daily_limit=limits.daily_min,
        daily_remain=remain_d,
        weekly_used=used_w,
        weekly_limit=limits.weekly_min,
        weekly_remain=remain_w,
        fortnight_used=used_f,
        fortnight_limit=limits.fortnight_min,
        fortnight_remain=remain_f,
        extensions_used=used_e,
        extensions_limit=limits.extensions,
        warning=warning,
        recorded_at=latest.recorded_at if latest else None,
        activity_status=state.activity_status if state else None,
        daily_rest_remain_min=state.daily_rest_remain_min if state else None,
        weekly_rest_remain_min=state.weekly_rest_remain_min if state else None,
    )
