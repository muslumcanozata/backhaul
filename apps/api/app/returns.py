from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.config import Settings
from app.matching import best_pairs
from app.models import Alert, Load, TachoState, TenantSettings, Vehicle
from app.netgsm import dispatch, drop_pending, queue_event
from app.planning import candidates
from app.tacho import reading_of


def solve_returns(db: Session, tenant_id, settings: TenantSettings, api_key: str | None, app_settings: Settings, opener=None) -> int:
    if settings.empty_km_cost is None or settings.loaded_km_cost is None:
        _cost_alert(db, tenant_id, present=True)
        db.commit()
        return 0
    _cost_alert(db, tenant_id, present=False)
    free = (
        db.query(Load)
        .filter(Load.tenant_id == tenant_id, Load.direction == "donus", Load.status.in_(("havuz", "onerildi", "atandi")), Load.locked == False)
        .all()
    )
    locked_vehicles = {
        row.vehicle_id
        for row in db.query(Load).filter(Load.tenant_id == tenant_id, Load.direction == "donus", Load.locked == True, Load.vehicle_id.is_not(None))
    }
    options: dict[tuple[str, str], dict] = {}
    benefits: dict[tuple[str, str], int] = {}
    for load in free:
        for row in candidates(db, settings, load, api_key):
            if not row["eligible"] or row["distance_quality"] != "google":
                continue
            if str(row["vehicle_id"]) in {str(item) for item in locked_vehicles}:
                continue
            vehicle = db.get(Vehicle, row["vehicle_id"])
            reading = reading_of(db.get(TachoState, vehicle.driver_id) if vehicle and vehicle.driver_id else None)
            if reading is not None and reading.source == "tahmini" and not settings.auto_assign_estimated:
                continue
            benefit = row["rank"]
            if benefit is None:
                continue
            if settings.reject_negative_benefit and benefit < 0:
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
    db.commit()
    return len(chosen)


def _stable(free: list[Load], settings: TenantSettings, benefits: dict[tuple[str, str], int]) -> list[tuple[str, str]]:
    chosen = best_pairs(benefits)
    current = [load for load in free if load.status == "atandi" and load.vehicle_id is not None]
    if not current:
        return chosen
    current_total = sum(int((load.benefit_try or 0) * 100) for load in current)
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
