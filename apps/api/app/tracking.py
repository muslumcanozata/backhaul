from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.live import hub
from app.models import Driver, Load, Vehicle, VehiclePosition


def snapshot(db: Session, tenant_id: UUID) -> list[dict]:
    vehicles = db.query(Vehicle).filter(Vehicle.tenant_id == tenant_id).order_by(Vehicle.plate).all()
    return [vehicle_point(db, vehicle) for vehicle in vehicles]


def announce(db: Session, tenant_id: UUID, vehicle: Vehicle) -> None:
    hub.publish(tenant_id, {"type": "position", "vehicle": vehicle_point(db, vehicle)})


def vehicle_point(db: Session, vehicle: Vehicle) -> dict:
    position = (
        db.query(VehiclePosition)
        .filter(VehiclePosition.vehicle_id == vehicle.id)
        .order_by(VehiclePosition.recorded_at.desc(), VehiclePosition.id.desc())
        .first()
    )
    driver = db.get(Driver, vehicle.driver_id) if vehicle.driver_id else None
    loaded = (
        db.query(Load.id)
        .filter(Load.vehicle_id == vehicle.id, Load.status.in_(("atandi", "yolda")))
        .first()
    )
    return {
        "id": str(vehicle.id),
        "plate": vehicle.plate,
        "status": vehicle.status,
        "duty": "yuklu" if loaded else "bos",
        "driver_name": driver.name if driver else None,
        "latitude": _coord(position.latitude) if position else None,
        "longitude": _coord(position.longitude) if position else None,
        "speed_kmh": _speed(position.speed_kmh) if position else None,
        "course": _speed(position.course) if position and position.course is not None else None,
        "recorded_at": _stamp(position.recorded_at) if position else None,
    }


def _coord(value: Decimal) -> str:
    return f"{value:.6f}"


def _speed(value: Decimal) -> str:
    return f"{value:.1f}"


def _stamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
