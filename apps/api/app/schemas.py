from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import TRAILER_CATALOG


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    role: str
    tenant_id: UUID | None
    active: bool = True


class UserAccessPatch(BaseModel):
    role: str | None = None
    active: bool | None = None


class TenantCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    code: str = Field(min_length=2, max_length=40, pattern=r"^[a-z0-9-]+$")


class TenantOut(BaseModel):
    id: UUID
    name: str
    code: str
    status: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    role: str


class SettingsPatch(BaseModel):
    enabled_trailer_types: list[str] | None = None
    empty_km_cost: Decimal | None = None
    loaded_km_cost: Decimal | None = None
    tacho_continuous_min: int | None = None
    tacho_daily_min: int | None = None
    tacho_extended_min: int | None = None
    tacho_extensions: int | None = None
    tacho_weekly_min: int | None = None
    tacho_fortnight_min: int | None = None
    tacho_warning_min: int | None = None
    return_approval: bool | None = None
    stability_percent: int | None = None
    reject_negative_benefit: bool | None = None
    auto_assign_estimated: bool | None = None

    def check_types(self) -> None:
        if self.enabled_trailer_types is None:
            return
        unknown = set(self.enabled_trailer_types) - set(TRAILER_CATALOG)
        if unknown or not self.enabled_trailer_types:
            raise ValueError("Kasa tipi katalogda olmalı")


class SettingsOut(BaseModel):
    enabled_trailer_types: list[str]
    empty_km_cost: Decimal | None
    loaded_km_cost: Decimal | None
    gps_stale_minutes: int
    arvento_configured: bool = False
    tacho_continuous_min: int = 270
    tacho_daily_min: int = 540
    tacho_extended_min: int = 600
    tacho_extensions: int = 2
    tacho_weekly_min: int = 3360
    tacho_fortnight_min: int = 5400
    tacho_warning_min: int = 30
    return_approval: bool = False
    stability_percent: int = 15
    reject_negative_benefit: bool = False
    auto_assign_estimated: bool = False
    netgsm_configured: bool = False


class NetgsmSecretIn(BaseModel):
    usercode: str = Field(min_length=1, max_length=40)
    password: str = Field(min_length=1, max_length=80)
    header: str = Field(min_length=1, max_length=11)


class ArventoSecretIn(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    pin1: str = Field(min_length=1, max_length=80)
    pin2: str = Field(min_length=1, max_length=80)


class VehicleCreate(BaseModel):
    plate: str = Field(min_length=5, max_length=20)
    capacity_tons: Decimal = Field(gt=0, le=100)
    trailer_type: str
    tare_tons: Decimal | None = Field(default=None, ge=0)
    device_id: str | None = None


class VehiclePatch(BaseModel):
    status: str | None = None
    driver_id: UUID | None = None


class VehicleOut(BaseModel):
    id: UUID
    plate: str
    capacity_tons: Decimal
    trailer_type: str
    tare_tons: Decimal | None
    status: str
    device_id: str | None
    driver_id: UUID | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    speed_kmh: Decimal | None = None
    recorded_at: datetime | None = None
    duty: str = "bos"
    tacho_source: str | None = None
    tacho_continuous_min: int | None = None
    tacho_daily_min: int | None = None
    tacho_weekly_min: int | None = None
    tacho_fortnight_min: int | None = None


class DriverCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    phone: str
    card_id: str | None = None


class DriverOut(BaseModel):
    id: UUID
    name: str
    phone: str
    card_id: str | None


class PositionCreate(BaseModel):
    latitude: Decimal = Field(ge=-90, le=90)
    longitude: Decimal = Field(ge=-180, le=180)
    speed_kmh: Decimal = Field(default=Decimal("0"), ge=0)
    recorded_at: datetime


class AlternativeOut(BaseModel):
    reference: str
    code: str


class LoadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reference: str
    direction: str
    customer: str | None
    broker_firm: str | None = None
    pickup_il: str
    pickup_ilce: str
    drop_il: str
    drop_ilce: str
    pickup_lat: Decimal | None
    pickup_lng: Decimal | None
    drop_lat: Decimal | None
    drop_lng: Decimal | None
    geocode_quality: str
    tonnage: Decimal
    trailer_type: str
    ready_at: datetime
    deliver_start: datetime
    deliver_end: datetime
    freight_try: Decimal | None
    status: str
    vehicle_id: UUID | None
    empty_km: Decimal | None
    loaded_km: Decimal | None
    distance_quality: str | None
    rank_value: Decimal | None
    benefit_try: Decimal | None = None
    locked: bool = False
    sms_status: str | None = None
    sms_job_id: str | None = None
    tacho_source: str | None = None
    tacho_continuous_min: int | None = None
    tacho_daily_min: int | None = None
    tacho_weekly_min: int | None = None
    tacho_continuous_remain: int | None = None
    tacho_daily_remain: int | None = None
    tacho_weekly_remain: int | None = None
    tacho_fortnight_remain: int | None = None
    planned_break_min: int | None = None
    calculated_at: datetime | None = None
    rule_pack: str = "TR-AETR-2026"
    empty_km_cost: Decimal | None = None
    loaded_km_cost: Decimal | None = None
    alternatives: list[AlternativeOut] = []


class LoadCreate(BaseModel):
    reference: str
    direction: str = "gidis"
    pickup_il: str
    pickup_ilce: str
    drop_il: str
    drop_ilce: str
    tonnage: Decimal
    trailer_type: str
    ready_at: datetime
    deliver_start: datetime
    deliver_end: datetime
    freight_try: Decimal | None = None
    customer: str | None = None
    broker_firm: str | None = None
    pickup_address: str | None = None
    drop_address: str | None = None


class LoadRevise(BaseModel):
    pickup_il: str | None = None
    pickup_ilce: str | None = None
    drop_il: str | None = None
    drop_ilce: str | None = None
    ready_at: datetime | None = None
    deliver_start: datetime | None = None
    deliver_end: datetime | None = None


class RowReject(BaseModel):
    row: int
    reference: str
    code: str


class ImportOut(BaseModel):
    accepted: int
    updated: int
    rejected: list[RowReject]


class CandidateOut(BaseModel):
    vehicle_id: UUID
    plate: str
    eligible: bool
    code: str | None
    empty_km: Decimal | None
    loaded_km: Decimal | None
    rank: Decimal | None
    distance_quality: str | None
    drive_min: int | None = None
    break_min: int | None = None
    uses_extension: bool = False


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vehicle_id: UUID | None
    code: str
    level: str
    measured: int
    limit_value: int
    seen_at: datetime | None


class AssignIn(BaseModel):
    vehicle_id: UUID


class PullOut(BaseModel):
    updated: int
    unmatched: list[str]
