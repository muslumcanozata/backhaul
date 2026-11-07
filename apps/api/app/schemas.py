from datetime import datetime
from decimal import Decimal
from uuid import UUID

from typing import Annotated

import email_validator
from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.models import TRAILER_CATALOG


# email-validator rejects ".local" even in test mode. The bootstrap admin uses it.
if "local" in email_validator.SPECIAL_USE_DOMAIN_NAMES:
    email_validator.SPECIAL_USE_DOMAIN_NAMES.remove("local")


def _app_email(value: str) -> str:
    domain = value.rsplit("@", 1)[-1].lower().rstrip(".")
    local_domain = domain == "local" or domain.endswith(".local")
    try:
        info = email_validator.validate_email(value, check_deliverability=not local_domain)
    except email_validator.EmailNotValidError as exc:
        raise ValueError(str(exc)) from exc
    return info.normalized


AppEmail = Annotated[str, AfterValidator(_app_email)]


class LoginRequest(BaseModel):
    email: AppEmail
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: AppEmail
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
    email: AppEmail
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
    arvento_enabled: bool | None = None
    seyir_enabled: bool | None = None
    home_base_il: str | None = None
    home_base_ilce: str | None = None
    toll_enabled: bool | None = None

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
    arvento_enabled: bool = False
    seyir_enabled: bool = False
    seyir_configured: bool = False
    enabled_telematics: list[str] = []
    home_base_il: str | None = None
    home_base_ilce: str | None = None
    toll_enabled: bool = False
    netgsm_configured: bool = False
    routes_today: int = 0
    routes_limit: int = 333
    routes_allowed: int = 333
    routes_cache_hits: int = 0
    routes_blocked: int = 0
    routes_needs_approval: bool = False


class SeyirSecretIn(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=80)


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
    toll_try: Decimal | None = None
    base_km: Decimal | None = None
    chain_value_try: Decimal | None = None
    chain_note: str | None = None
    driver_advice: str | None = None
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
    delivered_at: datetime | None = None
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
    toll_try: Decimal | None = None
    toll_unknown: bool = False
    base_km: Decimal | None = None
    plan_value: Decimal | None = None
    chain_note: str | None = None
    advice: str | None = None


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vehicle_id: UUID | None
    code: str
    level: str
    measured: int
    limit_value: int
    seen_at: datetime | None


class TachoSampleOut(BaseModel):
    recorded_at: datetime
    source: str
    continuous_min: int
    daily_min: int
    weekly_min: int
    fortnight_min: int
    extensions_used: int


class TachoDriverOut(BaseModel):
    driver_id: UUID
    name: str
    phone: str
    card_id: str | None
    plate: str | None
    source: str | None
    continuous_used: int
    continuous_limit: int
    continuous_remain: int
    daily_used: int
    daily_limit: int
    daily_remain: int
    weekly_used: int
    weekly_limit: int
    weekly_remain: int
    fortnight_used: int
    fortnight_limit: int
    fortnight_remain: int
    extensions_used: int
    extensions_limit: int
    warning: bool
    recorded_at: datetime | None


class TachoDriverDetailOut(TachoDriverOut):
    samples: list[TachoSampleOut] = []


class AssignIn(BaseModel):
    vehicle_id: UUID


class PullOut(BaseModel):
    updated: int
    unmatched: list[str]


class ReportKpi(BaseModel):
    key: str
    label: str
    value: str
    hint: str | None = None


class ReportSeriesPoint(BaseModel):
    name: str
    value: float


class ReportOut(BaseModel):
    slug: str
    title: str
    from_day: str
    to_day: str
    kpis: list[ReportKpi]
    series: list[ReportSeriesPoint] = []
    columns: list[str] = []
    rows: list[dict] = []


class MaintenanceCreate(BaseModel):
    kind: str = Field(pattern=r"^(periyodik|ariza|muayene|diger)$")
    happened_at: datetime
    odometer_km: Decimal | None = Field(default=None, ge=0)
    cost_try: Decimal | None = Field(default=None, ge=0)
    workshop: str | None = Field(default=None, max_length=200)
    note: str | None = Field(default=None, max_length=500)


class MaintenanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kind: str
    happened_at: datetime
    odometer_km: Decimal | None
    cost_try: Decimal | None
    workshop: str | None
    note: str | None
    source: str


class TireEventCreate(BaseModel):
    position: str = Field(pattern=r"^(FL|FR|RL|RR|RLO|RRO|stepne|diger)$")
    event: str = Field(pattern=r"^(takildi|sokuldu|degisti|basinc)$")
    brand_size: str | None = Field(default=None, max_length=120)
    odometer_km: Decimal | None = Field(default=None, ge=0)
    happened_at: datetime
    note: str | None = Field(default=None, max_length=500)


class TireEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    position: str
    event: str
    brand_size: str | None
    odometer_km: Decimal | None
    happened_at: datetime
    note: str | None
    source: str


class FuelFillCreate(BaseModel):
    happened_at: datetime
    liters: Decimal | None = Field(default=None, gt=0)
    amount_try: Decimal | None = Field(default=None, ge=0)
    odometer_km: Decimal | None = Field(default=None, ge=0)
    station: str | None = Field(default=None, max_length=200)
    note: str | None = Field(default=None, max_length=500)


class FuelFillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    happened_at: datetime
    liters: Decimal | None
    amount_try: Decimal | None
    odometer_km: Decimal | None
    station: str | None
    source: str
    note: str | None


class FuelSampleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    recorded_at: datetime
    level_pct: Decimal | None
    level_liters: Decimal | None
    odometer_km: Decimal | None


class DriverStintOut(BaseModel):
    id: UUID
    driver_id: UUID
    driver_name: str
    started_at: datetime
    ended_at: datetime | None
    source: str


class UsageLoadOut(BaseModel):
    id: UUID
    reference: str
    direction: str
    status: str
    ready_at: datetime
    delivered_at: datetime | None
    driver_id: UUID | None = None
    driver_name: str | None = None


class VehicleDossierOut(BaseModel):
    vehicle_id: UUID
    plate: str
    odometer_km: Decimal | None = None
    driver_id: UUID | None = None
    driver_name: str | None = None
    open_stint_started_at: datetime | None = None
    last_fuel_fill_at: datetime | None = None
    last_maintenance_at: datetime | None = None
    last_fuel_level_pct: Decimal | None = None
    maintenances: list[MaintenanceOut] = []
    tire_events: list[TireEventOut] = []
    fuel_fills: list[FuelFillOut] = []
    fuel_samples: list[FuelSampleOut] = []
    driver_stints: list[DriverStintOut] = []
    usage_loads: list[UsageLoadOut] = []
