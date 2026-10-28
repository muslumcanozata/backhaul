import base64
import json
import math
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.config import Settings
from app.crypto import open_secret, seal
from app.models import Alert, Driver, Load, SmsOutbox, Tenant, TenantSecret, Vehicle

ISTANBUL = ZoneInfo("Europe/Istanbul")
SEND_URL = "https://api.netgsm.com.tr/sms/rest/v2/send"
REPORT_URL = "https://api.netgsm.com.tr/sms/rest/v2/report"


class MissingNetgsm(Exception):
    pass


def save_credentials(db: Session, tenant_id, settings: Settings, usercode: str, password: str, header: str) -> None:
    if not settings.secrets_key:
        raise MissingNetgsm("Sır anahtarı yok")
    row = db.get(TenantSecret, tenant_id)
    if row is None:
        row = TenantSecret(tenant_id=tenant_id)
        db.add(row)
    row.netgsm_usercode = seal(settings.secrets_key, usercode)
    row.netgsm_password = seal(settings.secrets_key, password)
    row.netgsm_msgheader = seal(settings.secrets_key, header)


def credentials(db: Session, tenant_id, settings: Settings) -> tuple[str, str, str]:
    if settings.deployment_mode == "dedicated" and _env_ready(settings):
        return settings.netgsm_usercode or "", settings.netgsm_password or "", settings.netgsm_msgheader or ""
    row = db.get(TenantSecret, tenant_id)
    if row is None or not row.netgsm_usercode or not row.netgsm_password or not row.netgsm_msgheader:
        raise MissingNetgsm("Netgsm kaydı eksik")
    try:
        return (
            open_secret(settings.secrets_key, row.netgsm_usercode),
            open_secret(settings.secrets_key, row.netgsm_password),
            open_secret(settings.secrets_key, row.netgsm_msgheader),
        )
    except ValueError as exc:
        raise MissingNetgsm("Netgsm kaydı açılamadı") from exc


def queue_event(db: Session, tenant_id, load: Load, vehicle: Vehicle, event: str) -> SmsOutbox | None:
    existing = (
        db.query(SmsOutbox)
        .filter(
            SmsOutbox.load_id == load.id,
            SmsOutbox.vehicle_id == vehicle.id,
            SmsOutbox.event == event,
            SmsOutbox.status != "dustu",
        )
        .one_or_none()
    )
    if existing is not None:
        return existing
    driver = db.get(Driver, vehicle.driver_id) if vehicle.driver_id else None
    phone = driver.phone if driver else ""
    if len(phone) != 10 or not phone.startswith("5"):
        _alert(db, tenant_id, vehicle, "SMS_NO_PHONE")
        return None
    tenant = db.get(Tenant, tenant_id)
    body = render(tenant.name if tenant else "", load, vehicle.plate, event)
    row = SmsOutbox(
        tenant_id=tenant_id,
        load_id=load.id,
        vehicle_id=vehicle.id,
        driver_id=driver.id if driver else None,
        event=event,
        status="bekliyor",
        phone=phone,
        body=body,
        parts=max(1, math.ceil(len(body) / 155)),
    )
    db.add(row)
    db.flush()
    return row


def drop_pending(db: Session, load_id) -> None:
    rows = db.query(SmsOutbox).filter(SmsOutbox.load_id == load_id, SmsOutbox.status == "bekliyor").all()
    for row in rows:
        row.status = "dustu"


def dispatch(db: Session, tenant_id, settings: Settings, opener=urllib.request.urlopen) -> int:
    pending = (
        db.query(SmsOutbox)
        .filter(SmsOutbox.tenant_id == tenant_id, SmsOutbox.status == "bekliyor", SmsOutbox.attempts < 3)
        .all()
    )
    if not pending:
        return 0
    try:
        usercode, password, header = credentials(db, tenant_id, settings)
    except MissingNetgsm:
        return 0
    sent = 0
    for row in pending:
        row.attempts += 1
        try:
            job_id = transmit(usercode, password, header, row.phone, row.body, opener)
        except RuntimeError as exc:
            row.last_error = str(exc)[:80]
            _alert(db, tenant_id, db.get(Vehicle, row.vehicle_id), "SMS_REJECTED")
            continue
        row.status = "kabul"
        row.job_id = job_id
        row.last_error = None
        load = db.get(Load, row.load_id)
        if load is not None and row.event == "atama":
            load.locked = True
        sent += 1
    return sent


def poll_reports(db: Session, tenant_id, settings: Settings, opener=urllib.request.urlopen) -> int:
    rows = db.query(SmsOutbox).filter(SmsOutbox.tenant_id == tenant_id, SmsOutbox.status == "kabul", SmsOutbox.job_id.is_not(None)).all()
    if not rows:
        return 0
    try:
        usercode, password, _header = credentials(db, tenant_id, settings)
    except MissingNetgsm:
        return 0
    found = _report(usercode, password, [row.job_id or "" for row in rows], opener)
    updated = 0
    for row in rows:
        mark = found.get(row.job_id or "")
        if mark == "iletildi":
            row.status = "iletildi"
            updated += 1
        elif mark == "iletilemedi":
            row.status = "iletilemedi"
            vehicle = db.get(Vehicle, row.vehicle_id)
            _alert(db, tenant_id, vehicle, "SMS_UNDELIVERED")
            updated += 1
    return updated


def _report(usercode: str, password: str, job_ids: list[str], opener) -> dict[str, str]:
    token = base64.b64encode(f"{usercode}:{password}".encode()).decode()
    payload = {"appname": "backhaul", "jobids": job_ids}
    request = urllib.request.Request(
        REPORT_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Basic {token}"},
        method="POST",
    )
    with opener(request, timeout=20) as response:
        body = json.loads(response.read().decode())
    found: dict[str, str] = {}
    for item in body.get("jobs") or body.get("list") or []:
        job_id = str(item.get("jobid") or item.get("jobId") or "")
        status = str(item.get("status", ""))
        if status in {"1", "iletildi"}:
            found[job_id] = "iletildi"
        elif status in {"2", "3", "iletilemedi"}:
            found[job_id] = "iletilemedi"
    return found


def transmit(usercode: str, password: str, header: str, phone: str, text: str, opener) -> str:
    token = base64.b64encode(f"{usercode}:{password}".encode()).decode()
    payload = {
        "msgheader": header,
        "encoding": "TR",
        "iysfilter": "0",
        "appname": "backhaul",
        "messages": [{"msg": text, "no": phone}],
    }
    request = urllib.request.Request(
        SEND_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Basic {token}"},
        method="POST",
    )
    with opener(request, timeout=20) as response:
        raw = response.read().decode()
    body = json.loads(raw)
    code = str(body.get("code", ""))
    job_id = body.get("jobid") or body.get("jobId") or body.get("bulkid")
    if code != "00" or not job_id:
        raise RuntimeError(code or "SMS_REJECTED")
    return str(job_id)


def render(firm: str, load: Load, plate: str, event: str) -> str:
    if event == "iptal":
        return f"{firm} IPTAL {plate} Ref {load.reference} Bu sefer iptal edildi."
    label = "GUNCELLEME" if event == "guncelleme" else "ATAMA"
    direction = "GIDIS" if load.direction == "gidis" else "DONUS"
    return (
        f"{firm} {label} {direction} {plate} Ref {load.reference} "
        f"Yukleme {load.pickup_il}/{load.pickup_ilce} {_clock(load.ready_at)} "
        f"Bosaltma {load.drop_il}/{load.drop_ilce} "
        f"Teslim {_clock(load.deliver_start)}-{_clock(load.deliver_end)}"
    )


def _clock(value: datetime) -> str:
    if value.tzinfo is None:
        from datetime import UTC

        value = value.replace(tzinfo=UTC)
    return value.astimezone(ISTANBUL).strftime("%d.%m %H:%M")


def _env_ready(settings: Settings) -> bool:
    return bool(settings.netgsm_usercode and settings.netgsm_password and settings.netgsm_msgheader)


def _alert(db: Session, tenant_id, vehicle: Vehicle | None, code: str) -> None:
    if vehicle is None:
        return
    row = (
        db.query(Alert)
        .filter(Alert.tenant_id == tenant_id, Alert.vehicle_id == vehicle.id, Alert.code == code)
        .one_or_none()
    )
    if row is None:
        db.add(Alert(tenant_id=tenant_id, vehicle_id=vehicle.id, driver_id=vehicle.driver_id, code=code, level="uyari", measured=0, limit_value=0))
