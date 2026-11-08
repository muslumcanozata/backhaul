"""Araç özlük: şoför stintleri, Seyir yakıt örnekleri ve dolum adayları."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Vehicle, VehicleDriverStint, VehicleFuelFill, VehicleFuelSample

FUEL_RISE_PCT = Decimal("8")


def bind_driver(
    db: Session,
    vehicle: Vehicle,
    driver_id,
    *,
    source: str,
    at: datetime | None = None,
) -> None:
    """Araç şoförünü günceller; açık stinti kapatır, yenisini açar."""
    stamp = _as_utc(at) or datetime.now(UTC)
    current = vehicle.driver_id
    if current == driver_id:
        return
    if driver_id is not None:
        others = db.query(Vehicle).filter(Vehicle.driver_id == driver_id, Vehicle.id != vehicle.id).all()
        for other in others:
            _close_open_stint(db, other.id, stamp)
            other.driver_id = None
        if others:
            db.flush()
    _close_open_stint(db, vehicle.id, stamp)
    vehicle.driver_id = driver_id
    if driver_id is not None:
        db.add(
            VehicleDriverStint(
                tenant_id=vehicle.tenant_id,
                vehicle_id=vehicle.id,
                driver_id=driver_id,
                started_at=stamp,
                ended_at=None,
                source=source,
            )
        )
    db.flush()


def record_fuel_sample(
    db: Session,
    vehicle: Vehicle,
    *,
    recorded_at: datetime,
    level_pct: Decimal | None,
    level_liters: Decimal | None,
    odometer_km: Decimal | None,
) -> VehicleFuelSample | None:
    if level_pct is None and level_liters is None:
        return None
    stamp = _as_utc(recorded_at) or datetime.now(UTC)
    latest = (
        db.query(VehicleFuelSample)
        .filter(VehicleFuelSample.vehicle_id == vehicle.id)
        .order_by(VehicleFuelSample.recorded_at.desc())
        .first()
    )
    if latest is not None and _as_utc(latest.recorded_at) >= stamp:
        return None
    sample = VehicleFuelSample(
        tenant_id=vehicle.tenant_id,
        vehicle_id=vehicle.id,
        recorded_at=stamp,
        level_pct=level_pct,
        level_liters=level_liters,
        odometer_km=odometer_km,
    )
    db.add(sample)
    db.flush()
    _maybe_auto_fill(db, vehicle, latest, sample)
    return sample


def parse_fuel_fields(fields: dict[str, str]) -> tuple[Decimal | None, Decimal | None]:
    """Konum paketinden depo: 0–100 → %, aksi → litre. Bilinen alan adları denenir."""
    chosen: str | None = None
    raw: str | None = None
    for key in ("fuel_level", "tank_level", "fuel", "fuel_percent", "fuel_liters"):
        if fields.get(key):
            chosen, raw = key, fields[key]
            break
    if raw is None or chosen is None:
        return None, None
    try:
        value = Decimal(raw.replace(",", "."))
    except Exception:
        return None, None
    if chosen == "fuel_liters" or value > Decimal("100"):
        return None, value
    if Decimal("0") <= value <= Decimal("100"):
        return value, None
    return None, value


def _maybe_auto_fill(
    db: Session,
    vehicle: Vehicle,
    previous: VehicleFuelSample | None,
    sample: VehicleFuelSample,
) -> None:
    if previous is None or previous.level_pct is None or sample.level_pct is None:
        return
    rise = sample.level_pct - previous.level_pct
    if rise < FUEL_RISE_PCT:
        return
    db.add(
        VehicleFuelFill(
            tenant_id=vehicle.tenant_id,
            vehicle_id=vehicle.id,
            happened_at=sample.recorded_at,
            liters=None,
            amount_try=None,
            odometer_km=sample.odometer_km,
            station=None,
            source="seyir",
            note=f"Depo +{rise:.0f} puan (Seyir)",
        )
    )
    db.flush()


def _close_open_stint(db: Session, vehicle_id, stamp: datetime) -> None:
    open_stint = (
        db.query(VehicleDriverStint)
        .filter(VehicleDriverStint.vehicle_id == vehicle_id, VehicleDriverStint.ended_at.is_(None))
        .order_by(VehicleDriverStint.started_at.desc())
        .first()
    )
    if open_stint is not None:
        open_stint.ended_at = stamp


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
