import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.live import hub
from app.models import Driver, Load, Vehicle, VehiclePosition
from app.supabase_client import SupabaseError, broadcast

log = logging.getLogger("backhaul.live")


def snapshot(db: Session, tenant_id: UUID) -> list[dict]:
    # Supabase uzak DB: her sorgu ~60ms. Tek round-trip ile snapshot üret.
    if db.get_bind().dialect.name == "postgresql":
        return _snapshot_pg(db, tenant_id)
    return _snapshot_orm(db, tenant_id)


def _snapshot_pg(db: Session, tenant_id: UUID) -> list[dict]:
    rows = db.execute(
        text(
            """
            WITH fleet AS (
              SELECT id, plate, status, driver_id
              FROM vehicles
              WHERE tenant_id = :tenant_id
            ),
            latest AS (
              SELECT DISTINCT ON (vp.vehicle_id)
                     vp.vehicle_id, vp.latitude, vp.longitude, vp.speed_kmh, vp.course, vp.recorded_at
              FROM vehicle_positions vp
              JOIN fleet f ON f.id = vp.vehicle_id
              ORDER BY vp.vehicle_id, vp.recorded_at DESC, vp.id DESC
            ),
            busy AS (
              SELECT DISTINCT l.vehicle_id
              FROM loads l
              JOIN fleet f ON f.id = l.vehicle_id
              WHERE l.status IN ('atandi', 'yolda')
            )
            SELECT f.id, f.plate, f.status, d.name AS driver_name,
                   latest.latitude, latest.longitude, latest.speed_kmh, latest.course, latest.recorded_at,
                   (busy.vehicle_id IS NOT NULL) AS loaded
            FROM fleet f
            LEFT JOIN latest ON latest.vehicle_id = f.id
            LEFT JOIN drivers d ON d.id = f.driver_id
            LEFT JOIN busy ON busy.vehicle_id = f.id
            ORDER BY f.plate
            """
        ),
        {"tenant_id": tenant_id},
    ).mappings().all()
    return [
        {
            "id": str(row["id"]),
            "plate": row["plate"],
            "status": row["status"],
            "duty": "yuklu" if row["loaded"] else "bos",
            "driver_name": row["driver_name"],
            "latitude": _coord(row["latitude"]) if row["latitude"] is not None else None,
            "longitude": _coord(row["longitude"]) if row["longitude"] is not None else None,
            "speed_kmh": _speed(row["speed_kmh"]) if row["speed_kmh"] is not None else None,
            "course": _speed(row["course"]) if row["course"] is not None else None,
            "recorded_at": _stamp(row["recorded_at"]) if row["recorded_at"] is not None else None,
        }
        for row in rows
    ]


def _snapshot_orm(db: Session, tenant_id: UUID) -> list[dict]:
    vehicles = db.query(Vehicle).filter(Vehicle.tenant_id == tenant_id).order_by(Vehicle.plate).all()
    if not vehicles:
        return []
    vehicle_ids = [row.id for row in vehicles]
    positions = _latest_positions(db, vehicle_ids)
    busy = _busy_vehicle_ids(db, vehicle_ids)
    driver_ids = [row.driver_id for row in vehicles if row.driver_id is not None]
    drivers = {}
    if driver_ids:
        drivers = {row.id: row for row in db.query(Driver).filter(Driver.id.in_(driver_ids)).all()}
    return [
        _point(
            vehicle,
            position=positions.get(vehicle.id),
            driver=drivers.get(vehicle.driver_id) if vehicle.driver_id else None,
            loaded=vehicle.id in busy,
        )
        for vehicle in vehicles
    ]


def announce(db: Session, tenant_id: UUID, vehicle: Vehicle) -> None:
    message = {"type": "position", "vehicle": vehicle_point(db, vehicle)}
    hub.publish(tenant_id, message)
    settings = get_settings()
    if settings.supabase_enabled:
        try:
            broadcast(settings, tenant_id, "position", message)
        except SupabaseError:
            log.exception("Supabase Realtime yayın başarısız: %s", tenant_id)


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
    return _point(vehicle, position=position, driver=driver, loaded=loaded is not None)


def _point(
    vehicle: Vehicle,
    *,
    position: VehiclePosition | None,
    driver: Driver | None,
    loaded: bool,
) -> dict:
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


def _latest_positions(db: Session, vehicle_ids: list[UUID]) -> dict[UUID, VehiclePosition]:
    if not vehicle_ids:
        return {}
    if db.get_bind().dialect.name == "postgresql":
        rows = db.execute(
            text(
                """
                SELECT DISTINCT ON (vehicle_id)
                       id, vehicle_id, latitude, longitude, speed_kmh, course, odometer_km, recorded_at
                FROM vehicle_positions
                WHERE vehicle_id = ANY(:ids)
                ORDER BY vehicle_id, recorded_at DESC, id DESC
                """
            ),
            {"ids": vehicle_ids},
        ).mappings().all()
        out: dict[UUID, VehiclePosition] = {}
        for row in rows:
            pos = VehiclePosition(
                id=row["id"],
                vehicle_id=row["vehicle_id"],
                latitude=row["latitude"],
                longitude=row["longitude"],
                speed_kmh=row["speed_kmh"],
                course=row["course"],
                odometer_km=row["odometer_km"],
                recorded_at=row["recorded_at"],
            )
            out[pos.vehicle_id] = pos
        return out
    latest = (
        db.query(VehiclePosition.vehicle_id, func.max(VehiclePosition.recorded_at).label("recorded_at"))
        .filter(VehiclePosition.vehicle_id.in_(vehicle_ids))
        .group_by(VehiclePosition.vehicle_id)
        .subquery()
    )
    rows = (
        db.query(VehiclePosition)
        .join(
            latest,
            and_(
                VehiclePosition.vehicle_id == latest.c.vehicle_id,
                VehiclePosition.recorded_at == latest.c.recorded_at,
            ),
        )
        .all()
    )
    return {row.vehicle_id: row for row in rows}


def _busy_vehicle_ids(db: Session, vehicle_ids: list[UUID]) -> set[UUID]:
    rows = (
        db.query(Load.vehicle_id)
        .filter(Load.vehicle_id.in_(vehicle_ids), Load.status.in_(("atandi", "yolda")))
        .distinct()
        .all()
    )
    return {row[0] for row in rows if row[0] is not None}


def _coord(value: Decimal | float) -> str:
    return f"{Decimal(value):.6f}"


def _speed(value: Decimal | float) -> str:
    return f"{Decimal(value):.1f}"


def _stamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
