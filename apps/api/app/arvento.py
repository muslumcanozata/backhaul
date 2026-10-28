import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from xml.sax.saxutils import escape

import urllib.request
from sqlalchemy.orm import Session

from app.config import Settings
from app.crypto import open_secret, seal
from app.models import Driver, TenantSecret, TenantSettings, Vehicle, VehiclePosition
from app.tacho import observe, sync_alerts
from app.tracking import announce
from app.places import fold

ARVENTO_URL = "https://ws.arvento.com/v1/report.asmx"
SOAP_ACTION = "http://www.arvento.com/"


class ArventoError(RuntimeError):
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


def configured(db: Session, tenant_id, settings: Settings) -> bool:
    if _env_ready(settings):
        return True
    row = db.get(TenantSecret, tenant_id)
    return bool(row and row.arvento_username and row.arvento_pin1 and row.arvento_pin2)


def save_credentials(db: Session, tenant_id, settings: Settings, username: str, pin1: str, pin2: str) -> None:
    row = db.get(TenantSecret, tenant_id)
    if row is None:
        row = TenantSecret(tenant_id=tenant_id)
        db.add(row)
    row.arvento_username = seal(settings.secrets_key, username)
    row.arvento_pin1 = seal(settings.secrets_key, pin1)
    row.arvento_pin2 = seal(settings.secrets_key, pin2)


def credentials(db: Session, tenant_id, settings: Settings) -> tuple[str, str, str]:
    if settings.deployment_mode == "dedicated" and _env_ready(settings):
        return settings.arvento_username or "", settings.arvento_pin1 or "", settings.arvento_pin2 or ""
    row = db.get(TenantSecret, tenant_id)
    if row is None or not row.arvento_username or not row.arvento_pin1 or not row.arvento_pin2:
        raise MissingSecret("Arvento kaydı eksik")
    try:
        return (
            open_secret(settings.secrets_key, row.arvento_username),
            open_secret(settings.secrets_key, row.arvento_pin1),
            open_secret(settings.secrets_key, row.arvento_pin2),
        )
    except ValueError as exc:
        raise MissingSecret("Arvento kaydı açılamadı") from exc


def _env_ready(settings: Settings) -> bool:
    return bool(settings.arvento_username and settings.arvento_pin1 and settings.arvento_pin2)


def fetch_packets(
    username: str,
    pin1: str,
    pin2: str,
    opener=urllib.request.urlopen,
    url: str = ARVENTO_URL,
) -> list[Packet]:
    raw = _post(url, "GetVehicleStatusV4", username, pin1, pin2, opener)
    root = ET.fromstring(raw)
    if _fault(root):
        raw = _post(url, "GetVehicleStatusV3", username, pin1, pin2, opener)
        root = ET.fromstring(raw)
        if _fault(root):
            raise ArventoError("Arvento cevap vermedi")
    return parse_packets(root)


def parse_packets(root: ET.Element) -> list[Packet]:
    packets: list[Packet] = []
    for node in root.iter():
        if _local(node.tag) not in {"LastPacket", "LastPacketV4"}:
            continue
        fields = {_local(child.tag): (child.text or "").strip() for child in list(node)}
        latitude = _decimal(fields.get("dLatitude"))
        longitude = _decimal(fields.get("dLongitude"))
        recorded = _gmt(fields.get("dtGMTDateTime"))
        if latitude is None or longitude is None or recorded is None:
            continue
        can_km = _decimal(fields.get("dCANOdometerValue"))
        odometer = can_km if can_km is not None else _decimal(fields.get("dOdometer"))
        packets.append(
            Packet(
                node=fields.get("strNode") or None,
                plate=fields.get("strLicensePlate") or None,
                latitude=latitude,
                longitude=longitude,
                speed_kmh=_decimal(fields.get("dSpeed")) or Decimal("0"),
                course=_decimal(fields.get("nCourse")),
                recorded_at=recorded,
                odometer_km=odometer,
                driver_name=fields.get("strDriver") or None,
                identity_number=fields.get("strIdentityNumber") or None,
            )
        )
    return packets


def apply_packets(db: Session, tenant_id, packets: list[Packet]) -> tuple[int, list[str]]:
    vehicles = db.query(Vehicle).filter(Vehicle.tenant_id == tenant_id).all()
    by_plate = {vehicle.plate: vehicle for vehicle in vehicles}
    by_node = {vehicle.device_id: vehicle for vehicle in vehicles if vehicle.device_id}
    drivers = db.query(Driver).filter(Driver.tenant_id == tenant_id).all()
    updated = 0
    changed: list[Vehicle] = []
    unmatched: list[str] = []
    for packet in packets:
        vehicle = None
        if packet.plate:
            vehicle = by_plate.get(packet.plate.replace(" ", "").upper())
        if vehicle is None and packet.node:
            vehicle = by_node.get(packet.node)
        if vehicle is None:
            unmatched.append(packet.plate or packet.node or "")
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
        _match_driver(db, vehicle, drivers, packet)
        latest = (
            db.query(VehiclePosition)
            .filter(VehiclePosition.vehicle_id == vehicle.id)
            .order_by(VehiclePosition.recorded_at.desc())
            .first()
        )
        if latest is not None:
            observe(db, vehicle, latest)
            settings = db.get(TenantSettings, tenant_id)
            if settings is not None:
                sync_alerts(db, vehicle, settings)
        updated += 1
        changed.append(vehicle)
    db.commit()
    for vehicle in changed:
        announce(db, tenant_id, vehicle)
    return updated, unmatched


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
        previous.driver_id = None
        db.flush()
    vehicle.driver_id = chosen.id


def _post(url: str, method: str, username: str, pin1: str, pin2: str, opener) -> bytes:
    body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:a="http://www.arvento.com/">
  <soap:Body>
    <a:{method}>
      <a:Username>{escape(username)}</a:Username>
      <a:PIN1>{escape(pin1)}</a:PIN1>
      <a:PIN2>{escape(pin2)}</a:PIN2>
      <a:Language>TR</a:Language>
    </a:{method}>
  </soap:Body>
</soap:Envelope>""".encode()
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": f'"{SOAP_ACTION}{method}"'},
        method="POST",
    )
    with opener(request, timeout=30) as response:
        return response.read()


def _fault(root: ET.Element) -> bool:
    return any(_local(node.tag) == "Fault" for node in root.iter())


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _decimal(value: str | None) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(value.replace(",", "."))
    except InvalidOperation:
        return None


def _gmt(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if text.startswith("/Date(") and text.endswith(")/"):
        millis = int(text[6:-2].split("+", 1)[0].split("-", 1)[0])
        return datetime.fromtimestamp(millis / 1000, UTC)
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            parsed = datetime.strptime(text[:26], fmt)
            return parsed.replace(tzinfo=UTC)
        except ValueError:
            continue
    return None
