from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.geo import road_leg
from app.models import Load, TachoState, TenantSettings, Vehicle, VehiclePosition
from app.tacho import drive_minutes, fit, inserted_break, limits_from, reading_of, uses_extension

OPEN = ("atandi", "yolda")


def candidates(db: Session, settings: TenantSettings, load: Load, api_key: str | None) -> list[dict]:
    now = datetime.now(UTC)
    vehicles = db.query(Vehicle).filter(Vehicle.tenant_id == load.tenant_id).order_by(Vehicle.plate).all()
    rows: list[dict] = []
    for vehicle in vehicles:
        position = _latest(db, vehicle.id)
        open_load = (
            db.query(Load)
            .filter(Load.vehicle_id == vehicle.id, Load.status.in_(OPEN), Load.id != load.id)
            .order_by(Load.deliver_end.desc())
            .first()
        )
        code = _reject(vehicle, position, settings, load, open_load, now)
        empty_km = loaded_km = rank = None
        quality = None
        drive_min = break_min = None
        extension = False
        if code is None and load.pickup_lat is not None and load.drop_lat is not None and position is not None:
            origin = _origin(position, open_load, load)
            empty_km, empty_seconds, empty_quality = road_leg(db, origin, (load.pickup_lat, load.pickup_lng), api_key)
            loaded_km, loaded_seconds, loaded_quality = road_leg(db, (load.pickup_lat, load.pickup_lng), (load.drop_lat, load.drop_lng), api_key)
            quality = "google" if empty_quality == "google" and loaded_quality == "google" else "yaklasik"
            drive_min = drive_minutes(empty_seconds, loaded_seconds)
            limits = limits_from(settings)
            reading = reading_of(db.get(TachoState, vehicle.driver_id) if vehicle.driver_id else None)
            code = fit(reading, drive_min, limits)
            if code is None and reading is not None:
                break_min = inserted_break(reading.continuous_min, drive_min, limits.continuous_min)
                extension = uses_extension(reading, drive_min, limits)
                rank = _rank(load, settings, empty_km, loaded_km)
        rows.append(
            {
                "vehicle_id": vehicle.id,
                "plate": vehicle.plate,
                "eligible": code is None,
                "code": code,
                "empty_km": empty_km,
                "loaded_km": loaded_km,
                "rank": rank,
                "distance_quality": quality,
                "drive_min": drive_min,
                "break_min": break_min,
                "uses_extension": extension,
            }
        )
    rows.sort(key=lambda item: (item["eligible"], item["rank"] or Decimal("-1e18")), reverse=True)
    return rows


def assignment_for(db: Session, settings: TenantSettings, load: Load, vehicle: Vehicle, api_key: str | None) -> dict:
    row = next(item for item in candidates(db, settings, load, api_key) if item["vehicle_id"] == vehicle.id)
    if not row["eligible"]:
        raise ValueError(row["code"] or "VEHICLE_NOT_IN_SERVICE")
    return row


def _reject(vehicle: Vehicle, position: VehiclePosition | None, settings: TenantSettings, load: Load, open_load: Load | None, now: datetime) -> str | None:
    if vehicle.status != "serviste":
        return "VEHICLE_NOT_IN_SERVICE"
    recorded = _utc(position.recorded_at) if position is not None else None
    if recorded is None or now - recorded > timedelta(minutes=settings.gps_stale_minutes):
        return "STALE_POSITION"
    if vehicle.driver_id is None:
        return "NO_DRIVER"
    if load.tonnage > vehicle.capacity_tons:
        return "CAPACITY"
    if load.trailer_type != vehicle.trailer_type:
        return "TRAILER"
    if open_load is not None and _utc(open_load.deliver_end) > _utc(load.ready_at):
        return "OVERLAP"
    return None


def _origin(position: VehiclePosition, open_load: Load | None, load: Load) -> tuple[Decimal, Decimal]:
    if open_load is not None and open_load.drop_lat is not None and _utc(open_load.deliver_end) <= _utc(load.ready_at):
        return open_load.drop_lat, open_load.drop_lng
    return position.latitude, position.longitude


def _rank(load: Load, settings: TenantSettings, empty_km: Decimal, loaded_km: Decimal) -> Decimal:
    if load.freight_try is not None and settings.empty_km_cost is not None and settings.loaded_km_cost is not None:
        return load.freight_try - empty_km * settings.empty_km_cost - loaded_km * settings.loaded_km_cost
    return loaded_km - empty_km * Decimal("1.5")


def _latest(db: Session, vehicle_id) -> VehiclePosition | None:
    return (
        db.query(VehiclePosition)
        .filter(VehiclePosition.vehicle_id == vehicle_id)
        .order_by(VehiclePosition.recorded_at.desc())
        .first()
    )


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
