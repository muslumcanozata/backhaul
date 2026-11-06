import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from xml.sax.saxutils import escape

import urllib.request
from sqlalchemy.orm import Session

from app.config import Settings
from app.crypto import open_secret, seal
from app.dossier import bind_driver, parse_fuel_fields, record_fuel_sample
from app.models import Driver, TachoState, TenantSecret, TenantSettings, Vehicle, VehiclePosition
from app.places import fold
from app.tacho import record_sample, sync_alerts
from app.tracking import announce

SEYIR_URL = "https://ws.seyirmobil.com/LocationService.asmx"
NAMESPACE = "http://tempuri.org/"


class SeyirError(RuntimeError):
    pass


class MissingSecret(RuntimeError):
    pass


@dataclass(frozen=True)
class Packet:
    node: str | None
    plate: str | None
    latitude: Decimal
    longitude: Decimal
    speed_kmh: Decimal
    course: Decimal | None
    recorded_at: datetime
    odometer_km: Decimal | None
    driver_name: str | None
    identity_number: str | None
    fuel_level_pct: Decimal | None = None
    fuel_level_liters: Decimal | None = None


@dataclass(frozen=True)
class TachoPacket:
    driver_name: str | None
    driver_code: str | None
    plate: str | None
    recorded_at: datetime | None
    not_used_daily_drive: int | None
    not_used_weekly_drive: int | None
    total_double_weekly_drive: int | None
    remaining_drive_period: int | None
    not_used_drive_period: int | None
    remaining_long_drive_count: int | None


def configured(db: Session, tenant_id, settings: Settings) -> bool:
    if _env_ready(settings):
        return True
    row = db.get(TenantSecret, tenant_id)
    return bool(row and row.seyir_username and row.seyir_password)


def save_credentials(db: Session, tenant_id, settings: Settings, username: str, password: str) -> None:
    row = db.get(TenantSecret, tenant_id)
    if row is None:
        row = TenantSecret(tenant_id=tenant_id)
        db.add(row)
    row.seyir_username = seal(settings.secrets_key, username)
    row.seyir_password = seal(settings.secrets_key, password)


def credentials(db: Session, tenant_id, settings: Settings) -> tuple[str, str]:
    if settings.deployment_mode == "dedicated" and _env_ready(settings):
        return settings.seyir_username or "", settings.seyir_password or ""
    row = db.get(TenantSecret, tenant_id)
    if row is None or not row.seyir_username or not row.seyir_password:
        raise MissingSecret("Seyir kaydı eksik")
    try:
        return (
            open_secret(settings.secrets_key, row.seyir_username),
            open_secret(settings.secrets_key, row.seyir_password),
        )
    except ValueError as exc:
        raise MissingSecret("Seyir kaydı açılamadı") from exc


def _env_ready(settings: Settings) -> bool:
    return bool(settings.seyir_username and settings.seyir_password)


def fetch_packets(
    username: str,
    password: str,
    opener=urllib.request.urlopen,
    url: str = SEYIR_URL,
) -> list[Packet]:
    raw = _post(url, "GetActualLocations", username, password, opener)
    root = ET.fromstring(raw)
    if _fault(root):
        raise SeyirError("Seyir konum cevabı vermedi")
    return parse_packets(root)


def fetch_tacho(
    username: str,
    password: str,
    opener=urllib.request.urlopen,
    url: str = SEYIR_URL,
) -> list[TachoPacket]:
    raw = _post(url, "GetDriversLastTaviState", username, password, opener)
    root = ET.fromstring(raw)
    if _fault(root):
        raise SeyirError("Seyir takograf cevabı vermedi")
    return parse_tacho(root)


def parse_packets(root: ET.Element) -> list[Packet]:
    packets: list[Packet] = []
    for node in root.iter():
        if _local(node.tag) != "Table":
            continue
        fields = {_local(child.tag): (child.text or "").strip() for child in list(node)}
        if "latitude" not in fields and "vehicle" not in fields:
            continue
        latitude = _decimal(fields.get("latitude"))
        longitude = _decimal(fields.get("longitude"))
        recorded = _when(fields.get("data_time"))
        if latitude is None or longitude is None or recorded is None:
            continue
        fuel_pct, fuel_liters = parse_fuel_fields(fields)
        packets.append(
            Packet(
                node=fields.get("device_id") or None,
                plate=fields.get("vehicle") or None,
                latitude=latitude,
                longitude=longitude,
                speed_kmh=_decimal(fields.get("speed")) or Decimal("0"),
                course=_decimal(fields.get("angle")),
                recorded_at=recorded,
                odometer_km=_decimal(fields.get("total_km")),
                driver_name=fields.get("driver") or None,
                identity_number=fields.get("driver_key") or None,
                fuel_level_pct=fuel_pct,
                fuel_level_liters=fuel_liters,
            )
        )
    return packets


def parse_tacho(root: ET.Element) -> list[TachoPacket]:
    rows: list[TachoPacket] = []
    for node in root.iter():
        if _local(node.tag) != "Table":
            continue
        fields = {_local(child.tag): (child.text or "").strip() for child in list(node)}
        if "driver_code" not in fields and "not_used_daily_drive" not in fields:
            continue
        rows.append(
            TachoPacket(
                driver_name=fields.get("driver") or None,
                driver_code=fields.get("driver_code") or None,
                plate=fields.get("current_plate") or None,
                recorded_at=_when(fields.get("datetime_utc0")) or _when(fields.get("datetime_utc3")),
                not_used_daily_drive=_int(fields.get("not_used_daily_drive")),
                not_used_weekly_drive=_int(fields.get("not_used_weekly_drive")),
                total_double_weekly_drive=_int(fields.get("total_double_weekly_drive")),
                remaining_drive_period=_period(fields.get("remaining_drive_period")),
                not_used_drive_period=_period(fields.get("not_used_drive_period")),
                remaining_long_drive_count=_int(fields.get("remaining_long_drive_count")),
            )
        )
    return rows


def apply_packets(db: Session, tenant_id, packets: list[Packet]) -> tuple[int, list[str]]:
    vehicles = db.query(Vehicle).filter(Vehicle.tenant_id == tenant_id).all()
    by_plate = {_plate_key(vehicle.plate): vehicle for vehicle in vehicles}
    by_node = {vehicle.device_id: vehicle for vehicle in vehicles if vehicle.device_id}
    drivers = db.query(Driver).filter(Driver.tenant_id == tenant_id).all()
    updated = 0
    changed: list[Vehicle] = []
    unmatched: list[str] = []
    for packet in packets:
        vehicle = None
        if packet.plate:
            vehicle = by_plate.get(_plate_key(packet.plate))
        if vehicle is None and packet.node:
            vehicle = by_node.get(packet.node)
        if vehicle is None:
            unmatched.append(packet.plate or packet.node or "")
            continue
        latest = (
            db.query(VehiclePosition)
            .filter(VehiclePosition.vehicle_id == vehicle.id)
            .order_by(VehiclePosition.recorded_at.desc())
            .first()
        )
        if latest is not None and _as_utc(latest.recorded_at) >= _as_utc(packet.recorded_at):
            continue
        db.add(
            VehiclePosition(
                vehicle_id=vehicle.id,
                latitude=packet.latitude,
                longitude=packet.longitude,
                speed_kmh=packet.speed_kmh,
                course=packet.course,
                odometer_km=packet.odometer_km,
                recorded_at=packet.recorded_at,
            )
        )
        db.flush()
        record_fuel_sample(
            db,
            vehicle,
            recorded_at=packet.recorded_at,
            level_pct=packet.fuel_level_pct,
            level_liters=packet.fuel_level_liters,
            odometer_km=packet.odometer_km,
        )
        _match_driver(db, vehicle, drivers, packet)
        settings = db.get(TenantSettings, tenant_id)
        if settings is not None:
            sync_alerts(db, vehicle, settings)
        updated += 1
        changed.append(vehicle)
    db.flush()
    for vehicle in changed:
        announce(db, tenant_id, vehicle)
    return updated, unmatched


def apply_tacho(db: Session, tenant_id, packets: list[TachoPacket], settings: TenantSettings) -> int:
    drivers = db.query(Driver).filter(Driver.tenant_id == tenant_id).all()
    by_card = {driver.card_id: driver for driver in drivers if driver.card_id}
    vehicles = db.query(Vehicle).filter(Vehicle.tenant_id == tenant_id).all()
    by_plate = {_plate_key(vehicle.plate): vehicle for vehicle in vehicles}
    updated = 0
    # Seyir her sürücü kartı için geçmiş kayıt da döner. Eskiden yeniye işlenir, en yeni kayıt kalır.
    ordered = sorted(packets, key=lambda item: item.recorded_at or datetime.min.replace(tzinfo=UTC))
    for packet in ordered:
        driver = by_card.get(packet.driver_code or "")
        if driver is None and not packet.driver_code and packet.plate:
            vehicle = by_plate.get(_plate_key(packet.plate))
            if vehicle is not None and vehicle.driver_id is not None:
                driver = db.get(Driver, vehicle.driver_id)
        if driver is None:
            continue
        state = db.get(TachoState, driver.id)
        if state is None:
            state = TachoState(
                driver_id=driver.id,
                tenant_id=tenant_id,
                source="olculmus",
                continuous_min=0,
                daily_min=0,
                weekly_min=0,
                fortnight_min=0,
                extensions_used=0,
                split_break_min=0,
                day_key="",
                week_key="",
                fortnight_key="",
            )
            db.add(state)
        # Gerçek cevapta not_used_drive_period 270 dakikayı geçmez: kesintisiz sürüşten kalan süre budur.
        remaining_continuous = packet.not_used_drive_period
        if remaining_continuous is None:
            remaining_continuous = packet.remaining_drive_period
        state.source = "olculmus"
        state.daily_min = _used(settings.tacho_daily_min, packet.not_used_daily_drive)
        state.weekly_min = _used(settings.tacho_weekly_min, packet.not_used_weekly_drive)
        state.fortnight_min = max(0, packet.total_double_weekly_drive or 0)
        state.continuous_min = _used(settings.tacho_continuous_min, remaining_continuous)
        state.extensions_used = _used(settings.tacho_extensions, packet.remaining_long_drive_count)
        record_sample(db, state, packet.recorded_at)
        updated += 1
        vehicle = next((item for item in vehicles if item.driver_id == driver.id), None)
        if vehicle is not None:
            sync_alerts(db, vehicle, settings)
    db.flush()
    return updated


def _used(limit: int, remaining: int | None) -> int:
    if remaining is None:
        return 0
    return max(0, limit - remaining)


def _match_driver(db: Session, vehicle: Vehicle, drivers: list[Driver], packet: Packet) -> None:
    chosen: Driver | None = None
    if packet.identity_number:
        matches = [driver for driver in drivers if driver.card_id and driver.card_id == packet.identity_number]
        if len(matches) == 1:
            chosen = matches[0]
    if chosen is None and packet.driver_name:
        matches = [driver for driver in drivers if fold(driver.name) == fold(packet.driver_name or "")]
        if len(matches) == 1:
            chosen = matches[0]
    if chosen is None or vehicle.driver_id == chosen.id:
        return
    previous = db.query(Vehicle).filter(Vehicle.driver_id == chosen.id, Vehicle.id != vehicle.id).one_or_none()
    if previous is not None:
        bind_driver(db, previous, None, source="seyir", at=packet.recorded_at)
    bind_driver(db, vehicle, chosen.id, source="seyir", at=packet.recorded_at)


def _post(url: str, method: str, username: str, password: str, opener) -> bytes:
    body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:tem="{NAMESPACE}">
  <soap:Header/>
  <soap:Body>
    <tem:{method}>
      <tem:user_name>{escape(username)}</tem:user_name>
      <tem:password>{escape(password)}</tem:password>
    </tem:{method}>
  </soap:Body>
</soap:Envelope>""".encode()
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/soap+xml; charset=utf-8",
            "SOAPAction": f'"{NAMESPACE}{method}"',
        },
        method="POST",
    )
    with opener(request, timeout=30) as response:
        return response.read()


def _fault(root: ET.Element) -> bool:
    return any(_local(node.tag) == "Fault" for node in root.iter())


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _plate_key(value: str) -> str:
    return value.replace(" ", "").upper()


def _decimal(value: str | None) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(value.replace(",", "."))
    except InvalidOperation:
        return None


def _int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(Decimal(value.replace(",", ".")))
    except (InvalidOperation, ValueError):
        return None


def _period(value: str | None) -> int | None:
    parsed = _int(value)
    # 65535, cihazın "bilgi yok" değeridir.
    return None if parsed is not None and parsed >= 65535 else parsed


def _when(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                parsed = datetime.strptime(text[:26], fmt)
                return parsed.replace(tzinfo=UTC)
            except ValueError:
                continue
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
