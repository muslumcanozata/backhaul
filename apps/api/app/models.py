import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

TRAILER_CATALOG = ("tenteli", "frigolu", "sal", "lowbed", "tanker")


class VehicleStatus(str, enum.Enum):
    serviste = "serviste"
    bakimda = "bakimda"
    ariza = "ariza"


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    code: Mapped[str] = mapped_column(String(40), unique=True)
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Istanbul")
    status: Mapped[str] = mapped_column(String(20), default="active")
    settings: Mapped["TenantSettings"] = relationship(back_populates="tenant")


class TenantSettings(Base):
    __tablename__ = "tenant_settings"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), primary_key=True)
    enabled_trailer_types: Mapped[list[str]] = mapped_column(JSON, default=lambda: ["tenteli"])
    empty_km_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    loaded_km_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    gps_stale_minutes: Mapped[int] = mapped_column(default=15)
    tacho_continuous_min: Mapped[int] = mapped_column(default=270)
    tacho_daily_min: Mapped[int] = mapped_column(default=540)
    tacho_extended_min: Mapped[int] = mapped_column(default=600)
    tacho_extensions: Mapped[int] = mapped_column(default=2)
    tacho_weekly_min: Mapped[int] = mapped_column(default=3360)
    tacho_fortnight_min: Mapped[int] = mapped_column(default=5400)
    tacho_warning_min: Mapped[int] = mapped_column(default=30)
    return_approval: Mapped[bool] = mapped_column(default=False)
    stability_percent: Mapped[int] = mapped_column(default=15)
    reject_negative_benefit: Mapped[bool] = mapped_column(default=False)
    auto_assign_estimated: Mapped[bool] = mapped_column(default=False)
    tenant: Mapped[Tenant] = relationship(back_populates="settings")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tenants.id"), nullable=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(32))
    active: Mapped[bool] = mapped_column(default=True)


class Vehicle(Base):
    __tablename__ = "vehicles"
    __table_args__ = (UniqueConstraint("tenant_id", "plate", name="uq_vehicle_plate"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    driver_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("drivers.id"), nullable=True, unique=True)
    plate: Mapped[str] = mapped_column(String(20))
    capacity_tons: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    trailer_type: Mapped[str] = mapped_column(String(20))
    tare_tons: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=VehicleStatus.serviste.value)
    device_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    positions: Mapped[list["VehiclePosition"]] = relationship(back_populates="vehicle")


class Driver(Base):
    __tablename__ = "drivers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str] = mapped_column(String(10))
    card_id: Mapped[str | None] = mapped_column(String(40), nullable=True)


class VehiclePosition(Base):
    __tablename__ = "vehicle_positions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicles.id"), index=True)
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    speed_kmh: Mapped[Decimal] = mapped_column(Numeric(6, 1), default=0)
    course: Mapped[Decimal | None] = mapped_column(Numeric(6, 1), nullable=True)
    odometer_km: Mapped[Decimal | None] = mapped_column(Numeric(12, 1), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    vehicle: Mapped[Vehicle] = relationship(back_populates="positions")


class Load(Base):
    __tablename__ = "loads"
    __table_args__ = (UniqueConstraint("tenant_id", "reference", name="uq_load_reference"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    reference: Mapped[str] = mapped_column(String(80))
    direction: Mapped[str] = mapped_column(String(10))
    customer: Mapped[str | None] = mapped_column(String(200), nullable=True)
    broker_firm: Mapped[str | None] = mapped_column(String(200), nullable=True)
    pickup_il: Mapped[str] = mapped_column(String(80))
    pickup_ilce: Mapped[str] = mapped_column(String(80))
    pickup_address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    drop_il: Mapped[str] = mapped_column(String(80))
    drop_ilce: Mapped[str] = mapped_column(String(80))
    drop_address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    pickup_lat: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    pickup_lng: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    drop_lat: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    drop_lng: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    geocode_quality: Mapped[str] = mapped_column(String(20), default="yaklasik")
    tonnage: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    trailer_type: Mapped[str] = mapped_column(String(20))
    ready_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deliver_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deliver_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    freight_try: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(20), index=True)
    empty_km: Mapped[Decimal | None] = mapped_column(Numeric(8, 1), nullable=True)
    loaded_km: Mapped[Decimal | None] = mapped_column(Numeric(8, 1), nullable=True)
    distance_quality: Mapped[str | None] = mapped_column(String(20), nullable=True)
    rank_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    planned_drive_min: Mapped[int | None] = mapped_column(nullable=True)
    planned_break_min: Mapped[int | None] = mapped_column(nullable=True)
    calculated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    uses_extension: Mapped[bool] = mapped_column(default=False)
    benefit_try: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    locked: Mapped[bool] = mapped_column(default=False)


class TachoState(Base):
    __tablename__ = "tacho_states"

    driver_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("drivers.id"), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    source: Mapped[str] = mapped_column(String(20), default="tahmini")
    continuous_min: Mapped[int] = mapped_column(default=0)
    daily_min: Mapped[int] = mapped_column(default=0)
    weekly_min: Mapped[int] = mapped_column(default=0)
    fortnight_min: Mapped[int] = mapped_column(default=0)
    extensions_used: Mapped[int] = mapped_column(default=0)
    split_break_min: Mapped[int] = mapped_column(default=0)
    day_key: Mapped[str] = mapped_column(String(10), default="")
    week_key: Mapped[str] = mapped_column(String(10), default="")
    fortnight_key: Mapped[str] = mapped_column(String(10), default="")


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (UniqueConstraint("tenant_id", "vehicle_id", "code", name="uq_alert_code"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    driver_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("drivers.id"), nullable=True)
    code: Mapped[str] = mapped_column(String(40))
    level: Mapped[str] = mapped_column(String(20))
    measured: Mapped[int] = mapped_column(default=0)
    limit_value: Mapped[int] = mapped_column(default=0)
    seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TenantSecret(Base):
    __tablename__ = "tenant_secrets"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), primary_key=True)
    arvento_username: Mapped[str | None] = mapped_column(String(500), nullable=True)
    arvento_pin1: Mapped[str | None] = mapped_column(String(500), nullable=True)
    arvento_pin2: Mapped[str | None] = mapped_column(String(500), nullable=True)
    netgsm_usercode: Mapped[str | None] = mapped_column(String(500), nullable=True)
    netgsm_password: Mapped[str | None] = mapped_column(String(500), nullable=True)
    netgsm_msgheader: Mapped[str | None] = mapped_column(String(500), nullable=True)


class SmsOutbox(Base):
    __tablename__ = "sms_outbox"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    load_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("loads.id"), index=True)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicles.id"))
    driver_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("drivers.id"), nullable=True)
    event: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="bekliyor")
    phone: Mapped[str] = mapped_column(String(10))
    body: Mapped[str] = mapped_column(String(500))
    attempts: Mapped[int] = mapped_column(default=0)
    job_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    parts: Mapped[int] = mapped_column(default=1)
    last_error: Mapped[str | None] = mapped_column(String(80), nullable=True)


class RoadCache(Base):
    __tablename__ = "road_cache"

    cache_key: Mapped[str] = mapped_column(String(80), primary_key=True)
    kilometers: Mapped[Decimal] = mapped_column(Numeric(8, 1))
    seconds: Mapped[int] = mapped_column()
    quality: Mapped[str] = mapped_column(String(20))
