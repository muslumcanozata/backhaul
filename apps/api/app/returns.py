import hashlib
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.config import Settings
from app.geo import COARSE, _cell
from app.matching import best_pairs
from app.models import Alert, Load, TachoState, TenantSettings, Vehicle, VehiclePosition
from app.netgsm import dispatch, drop_pending, queue_event
from app.planning import candidates
from app.tacho import reading_of


def solve_returns(db: Session, tenant_id, settings: TenantSettings, api_key: str | None, app_settings: Settings, opener=None, force: bool = False) -> int:
    if settings.empty_km_cost is None or settings.loaded_km_cost is None:
        _cost_alert(db, tenant_id, present=True)
        db.commit()
        return 0
    _cost_alert(db, tenant_id, present=False)
    mark = planning_mark(db, tenant_id, settings)
    if not force and settings.planning_fingerprint == mark:
        if opener is None:
            dispatch(db, tenant_id, app_settings)
        else:
            dispatch(db, tenant_id, app_settings, opener)
        db.commit()
        return 0
    free = (
        db.query(Load)
        .filter(Load.tenant_id == tenant_id, Load.direction == "donus", Load.status.in_(("havuz", "onerildi", "atandi")), Load.locked == False)
        .all()
    )
    options: dict[tuple[str, str], dict] = {}
    benefits: dict[tuple[str, str], int] = {}
    memo: dict = {}
    for load in free:
        for row in candidates(db, settings, load, api_key, app_settings, free, memo=memo):
            if not row["eligible"] or row["distance_quality"] != "google":
                continue
            if row["toll_unknown"]:
                continue
            vehicle = db.get(Vehicle, row["vehicle_id"])
            reading = reading_of(db.get(TachoState, vehicle.driver_id) if vehicle and vehicle.driver_id else None)
            if reading is not None and reading.source == "tahmini" and not settings.auto_assign_estimated:
                continue
            benefit = row["plan_value"]
            if benefit is None or row["rank"] is None:
                continue
            if settings.reject_negative_benefit and row["rank"] < 0:
                continue
            pair = (str(load.id), str(row["vehicle_id"]))
            options[pair] = row
            benefits[pair] = int(Decimal(benefit) * 100)
    chosen = _stable(free, settings, benefits)
    chosen = [pair for pair in chosen if pair in options]
    _apply(db, tenant_id, settings, free, chosen, options)
    if opener is None:
        dispatch(db, tenant_id, app_settings)
    else:
        dispatch(db, tenant_id, app_settings, opener)
    db.flush()
    settings.planning_fingerprint = planning_mark(db, tenant_id, settings)
    db.commit()
    return len(chosen)


def planning_mark(db: Session, tenant_id, settings: TenantSettings) -> str:
    parts = [
        str(settings.empty_km_cost),
        str(settings.loaded_km_cost),
        settings.home_base_il or "",
        settings.home_base_ilce or "",
        str(int(bool(settings.toll_enabled))),
        str(int(bool(settings.reject_negative_benefit))),
        str(settings.stability_percent),
        str(int(bool(settings.auto_assign_estimated))),
        str(int(bool(settings.return_approval))),
    ]
    loads = (
        db.query(Load)
        .filter(Load.tenant_id == tenant_id, Load.direction == "donus", Load.status.in_(("havuz", "onerildi", "atandi")), Load.locked == False)
        .order_by(Load.id)
        .all()
    )
    for load in loads:
        parts.append(
            f"{load.id}:{load.status}:{load.vehicle_id}:{load.ready_at}:{load.deliver_end}:{load.freight_try}:{load.pickup_lat}:{load.drop_lat}:{load.tonnage}:{load.trailer_type}"
        )
    vehicles = db.query(Vehicle).filter(Vehicle.tenant_id == tenant_id).order_by(Vehicle.id).all()
    for vehicle in vehicles:
        position = (
            db.query(VehiclePosition)
            .filter(VehiclePosition.vehicle_id == vehicle.id)
            .order_by(VehiclePosition.recorded_at.desc())
            .first()
        )
        cell = "-"
        if position is not None:
            cell = f"{_cell(position.latitude, COARSE)}:{_cell(position.longitude, COARSE)}"
        open_load = (
            db.query(Load.id)
            .filter(Load.vehicle_id == vehicle.id, Load.status.in_(("atandi", "yolda")))
            .first()
        )
        tacho = db.get(TachoState, vehicle.driver_id) if vehicle.driver_id else None
        bucket = "-"
        if tacho is not None:
            bucket = f"{int(tacho.continuous_min or 0) // 30}:{int(tacho.daily_min or 0) // 30}:{tacho.source}"
        parts.append(f"{vehicle.id}:{vehicle.status}:{vehicle.driver_id}:{cell}:{open_load[0] if open_load else '-'}:{bucket}")
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def _stable(free: list[Load], settings: TenantSettings, benefits: dict[tuple[str, str], int]) -> list[tuple[str, str]]:
    chosen = best_pairs(benefits)
    current = [load for load in free if load.status == "atandi" and load.vehicle_id is not None]
    if not current:
        return chosen
    current_total = sum(int((load.chain_value_try if load.chain_value_try is not None else load.benefit_try or 0) * 100) for load in current)
    new_total = sum(benefits[pair] for pair in chosen)
    limit = current_total * (100 + settings.stability_percent) / 100
    if new_total > limit:
        return chosen
    frozen = {(str(load.id), str(load.vehicle_id)) for load in current}
    rest = {pair: value for pair, value in benefits.items() if pair[0] not in {item[0] for item in frozen} and pair[1] not in {item[1] for item in frozen}}
    return list(frozen) + best_pairs(rest)


def _apply(db: Session, tenant_id, settings: TenantSettings, free: list[Load], chosen: list[tuple[str, str]], options: dict[tuple[str, str], dict]) -> None:
    chosen_loads = {load_id for load_id, _ in chosen}
    status = "onerildi" if settings.return_approval else "atandi"
    for load in free:
        if str(load.id) in chosen_loads:
            continue
        if load.status == "havuz":
            continue
        _release(db, load)
    for load_id, vehicle_id in chosen:
        load = next(item for item in free if str(item.id) == load_id)
        row = options.get((load_id, vehicle_id))
        if row is None:
            continue
        vehicle = db.get(Vehicle, row["vehicle_id"])
        if vehicle is None:
            continue
        same = load.vehicle_id == vehicle.id and load.status == status
        if not same:
            _release(db, load)
        load.vehicle_id = vehicle.id
        load.status = status
        load.empty_km = row["empty_km"]
        load.loaded_km = row["loaded_km"]
        load.distance_quality = row["distance_quality"]
        load.rank_value = row["rank"]
        load.benefit_try = row["rank"]
        load.toll_try = row["toll_try"]
        load.base_km = row["base_km"]
        load.chain_value_try = row["plan_value"]
        load.chain_note = row["chain_note"]
        load.driver_advice = row["advice"]
        load.planned_drive_min = row["drive_min"]
        load.planned_break_min = row["break_min"]
        load.calculated_at = datetime.now(UTC)
        if row["uses_extension"] and not load.uses_extension and vehicle.driver_id is not None:
            _shift_extension(db, vehicle.driver_id, 1)
        load.uses_extension = bool(row["uses_extension"])
        if status == "atandi" and not same:
            queue_event(db, tenant_id, load, vehicle, "atama")


def _release(db: Session, load: Load) -> None:
    if load.uses_extension and load.vehicle_id is not None:
        vehicle = db.get(Vehicle, load.vehicle_id)
        if vehicle is not None and vehicle.driver_id is not None:
            _shift_extension(db, vehicle.driver_id, -1)
    drop_pending(db, load.id)
    load.vehicle_id = None
    load.status = "havuz"
    load.uses_extension = False
    load.benefit_try = None
    load.toll_try = None
    load.base_km = None
    load.chain_value_try = None
    load.chain_note = None
    load.driver_advice = None


def _shift_extension(db: Session, driver_id, delta: int) -> None:
    state = db.get(TachoState, driver_id)
    if state is None:
        return
    state.extensions_used = max(0, state.extensions_used + delta)


def _cost_alert(db: Session, tenant_id, present: bool) -> None:
    row = db.query(Alert).filter(Alert.tenant_id == tenant_id, Alert.code == "COST_RATES_MISSING").one_or_none()
    if present and row is None:
        db.add(Alert(tenant_id=tenant_id, code="COST_RATES_MISSING", level="uyari", measured=0, limit_value=0))
    if not present and row is not None:
        db.delete(row)
