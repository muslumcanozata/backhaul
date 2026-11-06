from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import get_db, require_operation_tenant, require_writer
from app.models import (
    Driver,
    Load,
    User,
    Vehicle,
    VehicleDriverStint,
    VehicleFuelFill,
    VehicleFuelSample,
    VehicleMaintenance,
    VehiclePosition,
    VehicleTireEvent,
)
from app.schemas import (
    FuelFillCreate,
    FuelFillOut,
    FuelSampleOut,
    MaintenanceCreate,
    MaintenanceOut,
    TireEventCreate,
    TireEventOut,
    VehicleDossierOut,
    DriverStintOut,
    UsageLoadOut,
)

router = APIRouter(tags=["dossier"])


def _vehicle(db: Session, tenant_id: UUID, vehicle_id: UUID) -> Vehicle:
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None or vehicle.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Araç yok")
    return vehicle


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


@router.get("/vehicles/{vehicle_id}/dossier", response_model=VehicleDossierOut)
def get_dossier(
    vehicle_id: UUID,
    tenant_id: UUID = Depends(require_operation_tenant),
    db: Session = Depends(get_db),
) -> VehicleDossierOut:
    vehicle = _vehicle(db, tenant_id, vehicle_id)
    drivers = {row.id: row for row in db.query(Driver).filter(Driver.tenant_id == tenant_id)}
    position = (
        db.query(VehiclePosition)
        .filter(VehiclePosition.vehicle_id == vehicle.id)
        .order_by(VehiclePosition.recorded_at.desc())
        .first()
    )
    maintenances = (
        db.query(VehicleMaintenance)
        .filter(VehicleMaintenance.vehicle_id == vehicle.id)
        .order_by(VehicleMaintenance.happened_at.desc())
        .limit(100)
        .all()
    )
    tires = (
        db.query(VehicleTireEvent)
        .filter(VehicleTireEvent.vehicle_id == vehicle.id)
        .order_by(VehicleTireEvent.happened_at.desc())
        .limit(100)
        .all()
    )
    fills = (
        db.query(VehicleFuelFill)
        .filter(VehicleFuelFill.vehicle_id == vehicle.id)
        .order_by(VehicleFuelFill.happened_at.desc())
        .limit(100)
        .all()
    )
    samples = (
        db.query(VehicleFuelSample)
        .filter(VehicleFuelSample.vehicle_id == vehicle.id)
        .order_by(VehicleFuelSample.recorded_at.desc())
        .limit(50)
        .all()
    )
    stints = (
        db.query(VehicleDriverStint)
        .filter(VehicleDriverStint.vehicle_id == vehicle.id)
        .order_by(VehicleDriverStint.started_at.desc())
        .limit(100)
        .all()
    )
    loads = (
        db.query(Load)
        .filter(Load.vehicle_id == vehicle.id, Load.status.in_(("atandi", "yolda", "teslim", "iptal")))
        .order_by(Load.ready_at.desc())
        .limit(100)
        .all()
    )
    open_stint = next((row for row in stints if row.ended_at is None), None)
    driver = drivers.get(vehicle.driver_id) if vehicle.driver_id else None
    return VehicleDossierOut(
        vehicle_id=vehicle.id,
        plate=vehicle.plate,
        odometer_km=position.odometer_km if position else None,
        driver_id=vehicle.driver_id,
        driver_name=driver.name if driver else None,
        open_stint_started_at=_as_utc(open_stint.started_at) if open_stint else None,
        last_fuel_fill_at=_as_utc(fills[0].happened_at) if fills else None,
        last_maintenance_at=_as_utc(maintenances[0].happened_at) if maintenances else None,
        last_fuel_level_pct=samples[0].level_pct if samples else None,
        maintenances=[_maintenance_out(row) for row in maintenances],
        tire_events=[_tire_out(row) for row in tires],
        fuel_fills=[_fill_out(row) for row in fills],
        fuel_samples=[_sample_out(row) for row in samples],
        driver_stints=[
            DriverStintOut(
                id=row.id,
                driver_id=row.driver_id,
                driver_name=drivers[row.driver_id].name if row.driver_id in drivers else "?",
                started_at=_as_utc(row.started_at) or row.started_at,
                ended_at=_as_utc(row.ended_at),
                source=row.source,
            )
            for row in stints
        ],
        usage_loads=[
            UsageLoadOut(
                id=row.id,
                reference=row.reference,
                direction=row.direction,
                status=row.status,
                ready_at=_as_utc(row.ready_at) or row.ready_at,
                delivered_at=_as_utc(row.delivered_at),
                driver_id=None,
                driver_name=None,
            )
            for row in loads
        ],
    )


@router.post("/vehicles/{vehicle_id}/maintenances", response_model=MaintenanceOut)
def add_maintenance(
    vehicle_id: UUID,
    body: MaintenanceCreate,
    tenant_id: UUID = Depends(require_operation_tenant),
    user: User = Depends(require_writer),
    db: Session = Depends(get_db),
) -> MaintenanceOut:
    vehicle = _vehicle(db, tenant_id, vehicle_id)
    row = VehicleMaintenance(
        tenant_id=tenant_id,
        vehicle_id=vehicle.id,
        kind=body.kind,
        happened_at=_as_utc(body.happened_at) or body.happened_at,
        odometer_km=body.odometer_km,
        cost_try=body.cost_try,
        workshop=body.workshop,
        note=body.note,
        source="manual",
        created_by=user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _maintenance_out(row)


@router.get("/vehicles/{vehicle_id}/maintenances", response_model=list[MaintenanceOut])
def list_maintenances(
    vehicle_id: UUID,
    tenant_id: UUID = Depends(require_operation_tenant),
    db: Session = Depends(get_db),
) -> list[MaintenanceOut]:
    _vehicle(db, tenant_id, vehicle_id)
    rows = (
        db.query(VehicleMaintenance)
        .filter(VehicleMaintenance.vehicle_id == vehicle_id)
        .order_by(VehicleMaintenance.happened_at.desc())
        .limit(200)
        .all()
    )
    return [_maintenance_out(row) for row in rows]


@router.post("/vehicles/{vehicle_id}/tire-events", response_model=TireEventOut)
def add_tire_event(
    vehicle_id: UUID,
    body: TireEventCreate,
    tenant_id: UUID = Depends(require_operation_tenant),
    user: User = Depends(require_writer),
    db: Session = Depends(get_db),
) -> TireEventOut:
    vehicle = _vehicle(db, tenant_id, vehicle_id)
    row = VehicleTireEvent(
        tenant_id=tenant_id,
        vehicle_id=vehicle.id,
        position=body.position,
        event=body.event,
        brand_size=body.brand_size,
        odometer_km=body.odometer_km,
        happened_at=_as_utc(body.happened_at) or body.happened_at,
        note=body.note,
        source="manual",
        created_by=user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _tire_out(row)


@router.get("/vehicles/{vehicle_id}/tire-events", response_model=list[TireEventOut])
def list_tire_events(
    vehicle_id: UUID,
    tenant_id: UUID = Depends(require_operation_tenant),
    db: Session = Depends(get_db),
) -> list[TireEventOut]:
    _vehicle(db, tenant_id, vehicle_id)
    rows = (
        db.query(VehicleTireEvent)
        .filter(VehicleTireEvent.vehicle_id == vehicle_id)
        .order_by(VehicleTireEvent.happened_at.desc())
        .limit(200)
        .all()
    )
    return [_tire_out(row) for row in rows]


@router.post("/vehicles/{vehicle_id}/fuel-fills", response_model=FuelFillOut)
def add_fuel_fill(
    vehicle_id: UUID,
    body: FuelFillCreate,
    tenant_id: UUID = Depends(require_operation_tenant),
    user: User = Depends(require_writer),
    db: Session = Depends(get_db),
) -> FuelFillOut:
    vehicle = _vehicle(db, tenant_id, vehicle_id)
    if body.liters is None and body.amount_try is None:
        raise HTTPException(status_code=422, detail="Litre veya tutar gerekli")
    row = VehicleFuelFill(
        tenant_id=tenant_id,
        vehicle_id=vehicle.id,
        happened_at=_as_utc(body.happened_at) or body.happened_at,
        liters=body.liters,
        amount_try=body.amount_try,
        odometer_km=body.odometer_km,
        station=body.station,
        source="manual",
        note=body.note,
        created_by=user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _fill_out(row)


@router.get("/vehicles/{vehicle_id}/fuel-fills", response_model=list[FuelFillOut])
def list_fuel_fills(
    vehicle_id: UUID,
    tenant_id: UUID = Depends(require_operation_tenant),
    db: Session = Depends(get_db),
) -> list[FuelFillOut]:
    _vehicle(db, tenant_id, vehicle_id)
    rows = (
        db.query(VehicleFuelFill)
        .filter(VehicleFuelFill.vehicle_id == vehicle_id)
        .order_by(VehicleFuelFill.happened_at.desc())
        .limit(200)
        .all()
    )
    return [_fill_out(row) for row in rows]


@router.get("/vehicles/{vehicle_id}/fuel-samples", response_model=list[FuelSampleOut])
def list_fuel_samples(
    vehicle_id: UUID,
    tenant_id: UUID = Depends(require_operation_tenant),
    db: Session = Depends(get_db),
) -> list[FuelSampleOut]:
    _vehicle(db, tenant_id, vehicle_id)
    rows = (
        db.query(VehicleFuelSample)
        .filter(VehicleFuelSample.vehicle_id == vehicle_id)
        .order_by(VehicleFuelSample.recorded_at.desc())
        .limit(200)
        .all()
    )
    return [_sample_out(row) for row in rows]


@router.get("/vehicles/{vehicle_id}/driver-stints", response_model=list[DriverStintOut])
def list_driver_stints(
    vehicle_id: UUID,
    tenant_id: UUID = Depends(require_operation_tenant),
    db: Session = Depends(get_db),
) -> list[DriverStintOut]:
    _vehicle(db, tenant_id, vehicle_id)
    drivers = {row.id: row.name for row in db.query(Driver).filter(Driver.tenant_id == tenant_id)}
    rows = (
        db.query(VehicleDriverStint)
        .filter(VehicleDriverStint.vehicle_id == vehicle_id)
        .order_by(VehicleDriverStint.started_at.desc())
        .limit(200)
        .all()
    )
    return [
        DriverStintOut(
            id=row.id,
            driver_id=row.driver_id,
            driver_name=drivers.get(row.driver_id, "?"),
            started_at=_as_utc(row.started_at) or row.started_at,
            ended_at=_as_utc(row.ended_at),
            source=row.source,
        )
        for row in rows
    ]


def _maintenance_out(row: VehicleMaintenance) -> MaintenanceOut:
    return MaintenanceOut(
        id=row.id,
        kind=row.kind,
        happened_at=_as_utc(row.happened_at) or row.happened_at,
        odometer_km=row.odometer_km,
        cost_try=row.cost_try,
        workshop=row.workshop,
        note=row.note,
        source=row.source,
    )


def _tire_out(row: VehicleTireEvent) -> TireEventOut:
    return TireEventOut(
        id=row.id,
        position=row.position,
        event=row.event,
        brand_size=row.brand_size,
        odometer_km=row.odometer_km,
        happened_at=_as_utc(row.happened_at) or row.happened_at,
        note=row.note,
        source=row.source,
    )


def _fill_out(row: VehicleFuelFill) -> FuelFillOut:
    return FuelFillOut(
        id=row.id,
        happened_at=_as_utc(row.happened_at) or row.happened_at,
        liters=row.liters,
        amount_try=row.amount_try,
        odometer_km=row.odometer_km,
        station=row.station,
        source=row.source,
        note=row.note,
    )


def _sample_out(row: VehicleFuelSample) -> FuelSampleOut:
    return FuelSampleOut(
        id=row.id,
        recorded_at=_as_utc(row.recorded_at) or row.recorded_at,
        level_pct=row.level_pct,
        level_liters=row.level_liters,
        odometer_km=row.odometer_km,
    )
