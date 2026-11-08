from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db, require_operation_tenant, require_writer
from app.arvento import MissingSecret, configured, save_credentials
import app.seyir as seyir
from app.netgsm import MissingNetgsm, dispatch
from app.netgsm import save_credentials as save_netgsm
from app.release import break_locked
from app.tacho import assert_tighter, observe, sync_alerts
from app.telematics import enabled_providers
from app.tracking import announce
from app.config import Settings
from app.deps import AppState, get_state
from app.dossier import bind_driver
from app.models import TRAILER_CATALOG, Driver, Load, TachoState, TenantSettings, User, Vehicle, VehiclePosition, VehicleStatus
from app.phones import normalize_phone
from app.places import find_place
from app.geo import approve_extra, usage_snapshot
from app.schemas import (
    DriverCreate,
    DriverOut,
    PositionCreate,
    ArventoSecretIn,
    NetgsmSecretIn,
    SeyirSecretIn,
    SettingsOut,
    SettingsPatch,
    VehicleCreate,
    VehicleOut,
    VehiclePatch,
)

router = APIRouter(tags=["fleet"])


def _settings_out(db: Session, tenant_id: UUID, settings: Settings) -> SettingsOut:
    row = _settings(db, tenant_id)
    return SettingsOut(
        enabled_trailer_types=row.enabled_trailer_types,
        empty_km_cost=row.empty_km_cost,
        loaded_km_cost=row.loaded_km_cost,
        gps_stale_minutes=row.gps_stale_minutes,
        arvento_configured=configured(db, tenant_id, settings),
        seyir_configured=seyir.configured(db, tenant_id, settings),
        arvento_enabled=bool(row.arvento_enabled),
        seyir_enabled=bool(row.seyir_enabled),
        enabled_telematics=enabled_providers(row),
        home_base_il=row.home_base_il,
        home_base_ilce=row.home_base_ilce,
        toll_enabled=bool(row.toll_enabled),
        tacho_continuous_min=row.tacho_continuous_min,
        tacho_daily_min=row.tacho_daily_min,
        tacho_extended_min=row.tacho_extended_min,
        tacho_extensions=row.tacho_extensions,
        tacho_weekly_min=row.tacho_weekly_min,
        tacho_fortnight_min=row.tacho_fortnight_min,
        tacho_warning_min=row.tacho_warning_min,
        return_approval=row.return_approval,
        stability_percent=row.stability_percent,
        reject_negative_benefit=row.reject_negative_benefit,
        auto_assign_estimated=row.auto_assign_estimated,
        netgsm_configured=_netgsm_configured(db, tenant_id, settings),
        **_routes_usage(db, settings),
    )


def _routes_usage(db: Session, settings: Settings) -> dict:
    return usage_snapshot(db, settings.routes_daily_limit)


def _netgsm_configured(db: Session, tenant_id: UUID, settings: Settings) -> bool:
    if settings.deployment_mode == "dedicated" and settings.netgsm_usercode and settings.netgsm_password and settings.netgsm_msgheader:
        return True
    from app.models import TenantSecret

    row = db.get(TenantSecret, tenant_id)
    return bool(row and row.netgsm_usercode and row.netgsm_password and row.netgsm_msgheader)


def _settings(db: Session, tenant_id: UUID) -> TenantSettings:
    row = db.get(TenantSettings, tenant_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Firma ayarı yok")
    return row


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _vehicle_out(
    db: Session,
    vehicle: Vehicle,
    *,
    position: VehiclePosition | None = None,
    duty: str | None = None,
    tacho: dict | None = None,
) -> VehicleOut:
    if position is None:
        position = (
            db.query(VehiclePosition)
            .filter(VehiclePosition.vehicle_id == vehicle.id)
            .order_by(VehiclePosition.recorded_at.desc())
            .first()
        )
    if duty is None:
        duty = _duty(db, vehicle.id)
    if tacho is None:
        tacho = _tacho_fields(db, vehicle)
    return VehicleOut(
        id=vehicle.id,
        plate=vehicle.plate,
        capacity_tons=vehicle.capacity_tons,
        trailer_type=vehicle.trailer_type,
        tare_tons=vehicle.tare_tons,
        status=vehicle.status,
        device_id=vehicle.device_id,
        driver_id=vehicle.driver_id,
        latitude=position.latitude if position else None,
        longitude=position.longitude if position else None,
        speed_kmh=position.speed_kmh if position else None,
        recorded_at=_as_utc(position.recorded_at) if position else None,
        duty=duty,
        **tacho,
    )


def _tacho_fields(db: Session, vehicle: Vehicle, state: TachoState | None = None) -> dict:
    if state is None and vehicle.driver_id is not None:
        state = db.get(TachoState, vehicle.driver_id)
    if state is None:
        return {}
    return {
        "tacho_source": state.source,
        "tacho_continuous_min": state.continuous_min,
        "tacho_daily_min": state.daily_min,
        "tacho_weekly_min": state.weekly_min,
        "tacho_fortnight_min": state.fortnight_min,
    }


def _duty(db: Session, vehicle_id: UUID) -> str:
    open_load = db.query(Load).filter(Load.vehicle_id == vehicle_id, Load.status.in_(("atandi", "yolda"))).first()
    return "yuklu" if open_load else "bos"


def _latest_positions(db: Session, vehicle_ids: list[UUID]) -> dict[UUID, VehiclePosition]:
    from app.tracking import _latest_positions as latest_positions

    return latest_positions(db, vehicle_ids)


def _busy_vehicle_ids(db: Session, vehicle_ids: list[UUID]) -> set[UUID]:
    if not vehicle_ids:
        return set()
    rows = (
        db.query(Load.vehicle_id)
        .filter(Load.vehicle_id.in_(vehicle_ids), Load.status.in_(("atandi", "yolda")))
        .distinct()
        .all()
    )
    return {row[0] for row in rows if row[0] is not None}


def _tacho_by_driver(db: Session, driver_ids: list[UUID]) -> dict[UUID, TachoState]:
    if not driver_ids:
        return {}
    rows = db.query(TachoState).filter(TachoState.driver_id.in_(driver_ids)).all()
    return {row.driver_id: row for row in rows}


@router.get("/settings", response_model=SettingsOut)
def read_settings(
    tenant_id: UUID = Depends(require_operation_tenant),
    db: Session = Depends(get_db),
    state: AppState = Depends(get_state),
) -> SettingsOut:
    return _settings_out(db, tenant_id, state.settings)


@router.patch("/settings", response_model=SettingsOut)
def patch_settings(
    body: SettingsPatch,
    tenant_id: UUID = Depends(require_operation_tenant),
    user: User = Depends(require_writer),
    db: Session = Depends(get_db),
    state: AppState = Depends(get_state),
) -> SettingsOut:
    if user.role != "tenant_admin":
        raise HTTPException(status_code=403, detail="Ayarları firma yöneticisi değiştirir")
    try:
        body.check_types()
        assert_tighter(
            continuous_min=body.tacho_continuous_min,
            daily_min=body.tacho_daily_min,
            extended_min=body.tacho_extended_min,
            extensions=body.tacho_extensions,
            weekly_min=body.tacho_weekly_min,
            fortnight_min=body.tacho_fortnight_min,
            warning_min=body.tacho_warning_min,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    row = _settings(db, tenant_id)
    rerun_returns = False
    if body.enabled_trailer_types is not None:
        row.enabled_trailer_types = body.enabled_trailer_types
    if body.empty_km_cost is not None:
        rerun_returns = True
        row.empty_km_cost = body.empty_km_cost
    if body.loaded_km_cost is not None:
        rerun_returns = True
        row.loaded_km_cost = body.loaded_km_cost
    if body.home_base_il is not None or body.home_base_ilce is not None:
        il = (body.home_base_il if body.home_base_il is not None else row.home_base_il or "").strip()
        ilce = (body.home_base_ilce if body.home_base_ilce is not None else row.home_base_ilce or "").strip()
        if il:
            if find_place(il, ilce or "Merkez") is None:
                raise HTTPException(status_code=422, detail="Üs noktası il ve ilçe katalogda yok")
            place = find_place(il, ilce or "Merkez")
            il, ilce = place.il, place.ilce
        else:
            il, ilce = None, None
        if (il, ilce) != (row.home_base_il, row.home_base_ilce):
            rerun_returns = True
        row.home_base_il, row.home_base_ilce = il, ilce
    for name in (
        "toll_enabled",
        "tacho_continuous_min",
        "tacho_daily_min",
        "tacho_extended_min",
        "tacho_extensions",
        "tacho_weekly_min",
        "tacho_fortnight_min",
        "tacho_warning_min",
        "return_approval",
        "stability_percent",
        "reject_negative_benefit",
        "auto_assign_estimated",
        "arvento_enabled",
        "seyir_enabled",
    ):
        value = getattr(body, name)
        if value is not None:
            if name in {"return_approval", "stability_percent", "reject_negative_benefit", "auto_assign_estimated", "toll_enabled"}:
                rerun_returns = rerun_returns or getattr(row, name) != value
            setattr(row, name, value)
    if row.tacho_extended_min < row.tacho_daily_min:
        raise HTTPException(status_code=422, detail="Uzatılmış günlük sürüş, günlük sınırın altında kalamaz")
    db.commit()
    db.refresh(row)
    if rerun_returns:
        from app.returns import solve_returns

        solve_returns(db, tenant_id, row, state.settings.google_maps_server_key, state.settings)
    return _settings_out(db, tenant_id, state.settings)


@router.put("/settings/arvento", response_model=SettingsOut)
def save_arvento(
    body: ArventoSecretIn,
    tenant_id: UUID = Depends(require_operation_tenant),
    user: User = Depends(require_writer),
    db: Session = Depends(get_db),
    state: AppState = Depends(get_state),
) -> SettingsOut:
    if user.role != "tenant_admin":
        raise HTTPException(status_code=403, detail="Arvento kaydını firma yöneticisi yazar")
    try:
        save_credentials(db, tenant_id, state.settings, body.username, body.pin1, body.pin2)
    except MissingSecret as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    return _settings_out(db, tenant_id, state.settings)


@router.put("/settings/seyir", response_model=SettingsOut)
def save_seyir(
    body: SeyirSecretIn,
    tenant_id: UUID = Depends(require_operation_tenant),
    user: User = Depends(require_writer),
    db: Session = Depends(get_db),
    state: AppState = Depends(get_state),
) -> SettingsOut:
    if user.role != "tenant_admin":
        raise HTTPException(status_code=403, detail="Seyir kaydını firma yöneticisi yazar")
    seyir.save_credentials(db, tenant_id, state.settings, body.username, body.password)
    db.commit()
    return _settings_out(db, tenant_id, state.settings)


@router.post("/settings/routes/approve", response_model=SettingsOut)
def approve_routes(
    tenant_id: UUID = Depends(require_operation_tenant),
    _: User = Depends(require_writer),
    db: Session = Depends(get_db),
    state: AppState = Depends(get_state),
) -> SettingsOut:
    approve_extra(db, extra=state.settings.routes_daily_limit)
    from app.returns import solve_returns

    solve_returns(db, tenant_id, _settings(db, tenant_id), state.settings.google_maps_server_key, state.settings, force=True)
    return _settings_out(db, tenant_id, state.settings)


@router.put("/settings/netgsm", response_model=SettingsOut)
def save_netgsm_account(
    body: NetgsmSecretIn,
    tenant_id: UUID = Depends(require_operation_tenant),
    user: User = Depends(require_writer),
    db: Session = Depends(get_db),
    state: AppState = Depends(get_state),
) -> SettingsOut:
    if user.role != "tenant_admin":
        raise HTTPException(status_code=403, detail="Netgsm kaydını firma yöneticisi yazar")
    try:
        save_netgsm(db, tenant_id, state.settings, body.usercode, body.password, body.header)
    except MissingNetgsm as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    return _settings_out(db, tenant_id, state.settings)


@router.get("/vehicles", response_model=list[VehicleOut])
def list_vehicles(tenant_id: UUID = Depends(require_operation_tenant), db: Session = Depends(get_db)) -> list[VehicleOut]:
    rows = db.query(Vehicle).filter(Vehicle.tenant_id == tenant_id).order_by(Vehicle.plate).all()
    ids = [row.id for row in rows]
    positions = _latest_positions(db, ids)
    busy = _busy_vehicle_ids(db, ids)
    states = _tacho_by_driver(db, [row.driver_id for row in rows if row.driver_id is not None])
    return [
        _vehicle_out(
            db,
            row,
            position=positions.get(row.id),
            duty="yuklu" if row.id in busy else "bos",
            tacho=_tacho_fields(db, row, states.get(row.driver_id) if row.driver_id else None),
        )
        for row in rows
    ]


@router.post("/vehicles", response_model=VehicleOut)
def create_vehicle(
    body: VehicleCreate,
    tenant_id: UUID = Depends(require_operation_tenant),
    user: User = Depends(require_writer),
    db: Session = Depends(get_db),
) -> VehicleOut:
    if user.role != "tenant_admin":
        raise HTTPException(status_code=403, detail="Aracı firma yöneticisi ekler")
    if body.trailer_type not in TRAILER_CATALOG:
        raise HTTPException(status_code=422, detail="Kasa tipi katalogda yok")
    settings = _settings(db, tenant_id)
    if body.trailer_type not in settings.enabled_trailer_types:
        raise HTTPException(status_code=422, detail="Firma bu kasa tipini açmamış")
    plate = body.plate.replace(" ", "").upper()
    exists = db.query(Vehicle).filter(Vehicle.tenant_id == tenant_id, Vehicle.plate == plate).one_or_none()
    if exists:
        raise HTTPException(status_code=409, detail="Plaka bu firmada kayıtlı")
    vehicle = Vehicle(
        tenant_id=tenant_id,
        plate=plate,
        capacity_tons=body.capacity_tons,
        trailer_type=body.trailer_type,
        tare_tons=body.tare_tons,
        device_id=body.device_id,
    )
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return _vehicle_out(db, vehicle)


@router.patch("/vehicles/{vehicle_id}", response_model=VehicleOut)
def patch_vehicle(
    vehicle_id: UUID,
    body: VehiclePatch,
    tenant_id: UUID = Depends(require_operation_tenant),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    state: AppState = Depends(get_state),
) -> VehicleOut:
    if user.role != "tenant_admin":
        raise HTTPException(status_code=403, detail="Araç kaydını firma yöneticisi değiştirir")
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None or vehicle.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Araç yok")
    changes = body.model_fields_set
    if "status" in changes and body.status is not None:
        if body.status not in {item.value for item in VehicleStatus}:
            raise HTTPException(status_code=422, detail="Durum serviste, bakımda veya arıza olmalı")
        vehicle.status = body.status
        if body.status in {"bakimda", "ariza"}:
            locked = db.query(Load).filter(Load.vehicle_id == vehicle.id, Load.locked == True, Load.status.in_(("atandi", "yolda"))).all()
            for load in locked:
                break_locked(db, load)
            dispatch(db, tenant_id, state.settings)
    if "driver_id" in changes:
        if body.driver_id is None:
            bind_driver(db, vehicle, None, source="manual")
        else:
            driver = db.get(Driver, body.driver_id)
            if driver is None or driver.tenant_id != tenant_id:
                raise HTTPException(status_code=404, detail="Şoför yok")
            previous = db.query(Vehicle).filter(Vehicle.driver_id == driver.id, Vehicle.id != vehicle.id).one_or_none()
            if previous is not None:
                bind_driver(db, previous, None, source="manual")
            bind_driver(db, vehicle, driver.id, source="manual")
    db.commit()
    db.refresh(vehicle)
    return _vehicle_out(db, vehicle)


@router.post("/vehicles/{vehicle_id}/position", response_model=VehicleOut)
def set_position(
    vehicle_id: UUID,
    body: PositionCreate,
    tenant_id: UUID = Depends(require_operation_tenant),
    _: User = Depends(require_writer),
    db: Session = Depends(get_db),
    state: AppState = Depends(get_state),
) -> VehicleOut:
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None or vehicle.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Araç yok")
    recorded = body.recorded_at
    if recorded.tzinfo is None:
        recorded = recorded.replace(tzinfo=UTC)
    position = VehiclePosition(
        vehicle_id=vehicle.id,
        latitude=body.latitude,
        longitude=body.longitude,
        speed_kmh=body.speed_kmh,
        recorded_at=recorded,
    )
    db.add(position)
    db.flush()
    observe(db, vehicle, position)
    sync_alerts(db, vehicle, _settings(db, tenant_id))
    dispatch(db, tenant_id, state.settings)
    db.commit()
    announce(db, tenant_id, vehicle)
    db.refresh(vehicle)
    return _vehicle_out(db, vehicle)


@router.get("/drivers", response_model=list[DriverOut])
def list_drivers(tenant_id: UUID = Depends(require_operation_tenant), db: Session = Depends(get_db)) -> list[Driver]:
    return db.query(Driver).filter(Driver.tenant_id == tenant_id).order_by(Driver.name).all()


@router.post("/drivers", response_model=DriverOut)
def create_driver(
    body: DriverCreate,
    tenant_id: UUID = Depends(require_operation_tenant),
    user: User = Depends(require_writer),
    db: Session = Depends(get_db),
) -> Driver:
    if user.role != "tenant_admin":
        raise HTTPException(status_code=403, detail="Şoförü firma yöneticisi ekler")
    try:
        phone = normalize_phone(body.phone)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    driver = Driver(tenant_id=tenant_id, name=body.name, phone=phone, card_id=body.card_id)
    db.add(driver)
    db.commit()
    db.refresh(driver)
    return driver
