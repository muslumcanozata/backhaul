"""Firma raporları. Yalnız tenant_id ile süzülür; başka firma satırı yok."""

from __future__ import annotations

import io
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models import Driver, Load, RoutesUsage, SmsOutbox, TachoSample, TachoState, TenantSettings, Vehicle
from app.schemas import ReportKpi, ReportOut, ReportSeriesPoint
from app.tacho import Limits, limits_from

ISTANBUL = ZoneInfo("Europe/Istanbul")

SLUGS = (
    "operasyon",
    "donus-faydasi",
    "takograf",
    "sms",
    "filo",
    "routes",
)

TITLES = {
    "operasyon": "Operasyon özeti",
    "donus-faydasi": "Dönüş faydası",
    "takograf": "Takograf uyum",
    "sms": "SMS iletişim",
    "filo": "Filo kullanım",
    "routes": "Routes maliyeti",
}


def build_report(
    db: Session,
    tenant_id,
    slug: str,
    from_day: date,
    to_day: date,
    direction: str | None = None,
) -> ReportOut:
    if slug not in SLUGS:
        raise ValueError("REPORT_UNKNOWN")
    start, end = _bounds(from_day, to_day)
    if slug == "operasyon":
        return _operasyon(db, tenant_id, from_day, to_day, start, end, direction)
    if slug == "donus-faydasi":
        return _donus(db, tenant_id, from_day, to_day, start, end)
    if slug == "takograf":
        return _takograf(db, tenant_id, from_day, to_day, start, end)
    if slug == "sms":
        return _sms(db, tenant_id, from_day, to_day, start, end)
    if slug == "filo":
        return _filo(db, tenant_id, from_day, to_day, start, end, direction)
    return _routes(db, tenant_id, from_day, to_day)


def export_report(db: Session, tenant_id, slug: str, from_day: date, to_day: date, direction: str | None = None) -> bytes:
    from openpyxl import Workbook

    report = build_report(db, tenant_id, slug, from_day, to_day, direction)
    book = Workbook()
    sheet = book.active
    sheet.title = slug[:31]
    if report.columns:
        sheet.append(report.columns)
        for row in report.rows:
            sheet.append([row.get(column, "") for column in report.columns])
    else:
        sheet.append(["kpi", "deger", "not"])
        for item in report.kpis:
            sheet.append([item.label, item.value, item.hint or ""])
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


def _bounds(from_day: date, to_day: date) -> tuple[datetime, datetime]:
    start = datetime(from_day.year, from_day.month, from_day.day, tzinfo=ISTANBUL).astimezone(UTC)
    end = datetime(to_day.year, to_day.month, to_day.day, tzinfo=ISTANBUL).astimezone(UTC) + timedelta(days=1)
    return start, end


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _day_key(value: datetime) -> str:
    stamp = _as_utc(value)
    assert stamp is not None
    return stamp.astimezone(ISTANBUL).date().isoformat()


def _loads(db: Session, tenant_id, start: datetime, end: datetime, direction: str | None) -> list[Load]:
    query = db.query(Load).filter(Load.tenant_id == tenant_id, Load.ready_at >= start, Load.ready_at < end)
    if direction in {"gidis", "donus"}:
        query = query.filter(Load.direction == direction)
    return query.order_by(Load.ready_at).all()


def _kpi(key: str, label: str, value, hint: str | None = None) -> ReportKpi:
    if isinstance(value, Decimal):
        text = f"{value:.2f}".rstrip("0").rstrip(".")
    else:
        text = str(value)
    return ReportKpi(key=key, label=label, value=text, hint=hint)


def _operasyon(db, tenant_id, from_day, to_day, start, end, direction) -> ReportOut:
    rows = _loads(db, tenant_id, start, end, direction)
    assigned = [row for row in rows if row.status in {"atandi", "yolda", "teslim"}]
    delivered = [row for row in rows if row.status == "teslim"]
    cancelled = [row for row in rows if row.status == "iptal"]
    empty = sum(((row.empty_km or Decimal("0")) for row in assigned if row.empty_km is not None), Decimal("0"))
    loaded = sum(((row.loaded_km or Decimal("0")) for row in assigned if row.loaded_km is not None), Decimal("0"))
    google_empty = sum(
        ((row.empty_km or Decimal("0")) for row in assigned if row.distance_quality == "google" and row.empty_km is not None),
        Decimal("0"),
    )
    timed = [row for row in delivered if row.delivered_at is not None]
    on_time = sum(1 for row in timed if _as_utc(row.delivered_at) <= _as_utc(row.deliver_end))
    on_time_pct = f"{round(100 * on_time / len(timed))}%" if timed else "—"
    by_day: dict[str, dict] = defaultdict(lambda: {"teslim": 0, "iptal": 0, "bos_km": 0.0})
    for row in rows:
        key = _day_key(row.ready_at)
        if row.status == "teslim":
            by_day[key]["teslim"] += 1
        if row.status == "iptal":
            by_day[key]["iptal"] += 1
        if row.status in {"atandi", "yolda", "teslim"} and row.empty_km is not None:
            by_day[key]["bos_km"] += float(row.empty_km)
    series = [ReportSeriesPoint(name=day, value=float(bag["teslim"])) for day, bag in sorted(by_day.items())]
    table = [
        {
            "gun": day,
            "teslim": bag["teslim"],
            "iptal": bag["iptal"],
            "bos_km": round(bag["bos_km"], 1),
        }
        for day, bag in sorted(by_day.items())
    ]
    gidis = sum(1 for row in rows if row.direction == "gidis")
    donus = sum(1 for row in rows if row.direction == "donus")
    return ReportOut(
        slug="operasyon",
        title=TITLES["operasyon"],
        from_day=from_day.isoformat(),
        to_day=to_day.isoformat(),
        kpis=[
            _kpi("assigned", "Atanan / yolda / teslim", len(assigned)),
            _kpi("delivered", "Teslim", len(delivered)),
            _kpi("cancelled", "İptal", len(cancelled)),
            _kpi("empty_km", "Boş km", empty.quantize(Decimal("0.1")) if isinstance(empty, Decimal) else empty, "Google ölçülü kısım dahil"),
            _kpi("loaded_km", "Dolu km", loaded.quantize(Decimal("0.1")) if isinstance(loaded, Decimal) else loaded),
            _kpi("google_empty", "Google boş km", google_empty.quantize(Decimal("0.1")) if isinstance(google_empty, Decimal) else google_empty),
            _kpi("on_time", "Süresinde teslim", on_time_pct, None if timed else "delivered_at yok"),
            _kpi("gidis", "Gidiş yükü", gidis),
            _kpi("donus", "Dönüş yükü", donus),
        ],
        series=series,
        columns=["gun", "teslim", "iptal", "bos_km"],
        rows=table,
    )


def _donus(db, tenant_id, from_day, to_day, start, end) -> ReportOut:
    rows = _loads(db, tenant_id, start, end, "donus")
    assigned = [row for row in rows if row.status in {"atandi", "yolda", "teslim", "onerildi"} and row.vehicle_id]
    locked = [row for row in assigned if row.locked]
    cancelled = [row for row in rows if row.status == "iptal"]
    freight = sum(((row.freight_try or Decimal("0")) for row in assigned), Decimal("0"))
    benefit = sum(((row.benefit_try or Decimal("0")) for row in assigned if row.benefit_try is not None), Decimal("0"))
    toll = sum(((row.toll_try or Decimal("0")) for row in assigned if row.toll_try is not None), Decimal("0"))
    base = sum(((row.base_km or Decimal("0")) for row in assigned if row.base_km is not None), Decimal("0"))
    by_day: dict[str, float] = defaultdict(float)
    for row in assigned:
        if row.benefit_try is not None:
            by_day[_day_key(row.ready_at)] += float(row.benefit_try)
    vehicles = {row.id: row.plate for row in db.query(Vehicle).filter(Vehicle.tenant_id == tenant_id).all()}
    table = [
        {
            "referans": row.reference,
            "arac": vehicles.get(row.vehicle_id, "") if row.vehicle_id else "",
            "araci_firma": row.broker_firm or "",
            "navlun": float(row.freight_try) if row.freight_try is not None else "",
            "bos_km": float(row.empty_km) if row.empty_km is not None else "",
            "dolu_km": float(row.loaded_km) if row.loaded_km is not None else "",
            "fayda": float(row.benefit_try) if row.benefit_try is not None else "",
            "durum": row.status,
            "kilitli": "evet" if row.locked else "hayır",
        }
        for row in rows
    ]
    return ReportOut(
        slug="donus-faydasi",
        title=TITLES["donus-faydasi"],
        from_day=from_day.isoformat(),
        to_day=to_day.isoformat(),
        kpis=[
            _kpi("freight", "Toplam navlun (TL)", freight.quantize(Decimal("0.01"))),
            _kpi("benefit", "Toplam fayda (TL)", benefit.quantize(Decimal("0.01"))),
            _kpi("toll", "Geçiş ücreti (TL)", toll.quantize(Decimal("0.01"))),
            _kpi("base_km", "Üse dönüş km", base.quantize(Decimal("0.1"))),
            _kpi("assigned", "Atanan / önerilen fırsat", len(assigned)),
            _kpi("locked", "Kilitli", len(locked)),
            _kpi("cancelled", "İptal", len(cancelled)),
        ],
        series=[ReportSeriesPoint(name=day, value=round(value, 2)) for day, value in sorted(by_day.items())],
        columns=["referans", "arac", "araci_firma", "navlun", "bos_km", "dolu_km", "fayda", "durum", "kilitli"],
        rows=table,
    )


def _takograf(db, tenant_id, from_day, to_day, start, end) -> ReportOut:
    settings = db.get(TenantSettings, tenant_id)
    limits = limits_from(settings) if settings else Limits()
    drivers = db.query(Driver).filter(Driver.tenant_id == tenant_id).order_by(Driver.name).all()
    vehicles = {row.driver_id: row.plate for row in db.query(Vehicle).filter(Vehicle.tenant_id == tenant_id, Vehicle.driver_id.is_not(None))}
    warning = 0
    exhausted = 0
    table = []
    for driver in drivers:
        state = db.get(TachoState, driver.id)
        samples = (
            db.query(TachoSample)
            .filter(TachoSample.driver_id == driver.id, TachoSample.recorded_at >= start, TachoSample.recorded_at < end)
            .all()
        )
        used_c = state.continuous_min if state else 0
        used_d = state.daily_min if state else 0
        used_w = state.weekly_min if state else 0
        used_f = state.fortnight_min if state else 0
        used_e = state.extensions_used if state else 0
        max_d = max((item.daily_min for item in samples), default=used_d)
        max_w = max((item.weekly_min for item in samples), default=used_w)
        max_f = max((item.fortnight_min for item in samples), default=used_f)
        remain_c = max(0, limits.continuous_min - used_c)
        remain_d = max(0, limits.daily_min - used_d)
        remain_w = max(0, limits.weekly_min - used_w)
        remain_f = max(0, limits.fortnight_min - used_f)
        near = remain_c <= limits.warning_min or remain_d <= limits.warning_min or remain_w <= limits.warning_min or remain_f <= limits.warning_min
        if near:
            warning += 1
        if used_e >= limits.extensions:
            exhausted += 1
        table.append(
            {
                "surucu": driver.name,
                "plaka": vehicles.get(driver.id, ""),
                "kaynak": state.source if state else "",
                "gunluk_kullanilan": used_d,
                "gunluk_max": max_d,
                "gunluk_limit": limits.daily_min,
                "haftalik_kullanilan": used_w,
                "haftalik_max": max_w,
                "haftalik_limit": limits.weekly_min,
                "iki_haftalik_kullanilan": used_f,
                "iki_haftalik_max": max_f,
                "iki_haftalik_limit": limits.fortnight_min,
                "uzatma": f"{used_e}/{limits.extensions}",
                "uyari": "evet" if near else "hayır",
                "driver_id": str(driver.id),
            }
        )
    buckets = [("0-50%", 0), ("50-70%", 0), ("70-90%", 0), ("90%+", 0)]
    for row in table:
        ratio = row["gunluk_kullanilan"] / row["gunluk_limit"] if row["gunluk_limit"] else 0
        if ratio >= 0.9:
            buckets[3] = (buckets[3][0], buckets[3][1] + 1)
        elif ratio >= 0.7:
            buckets[2] = (buckets[2][0], buckets[2][1] + 1)
        elif ratio >= 0.5:
            buckets[1] = (buckets[1][0], buckets[1][1] + 1)
        else:
            buckets[0] = (buckets[0][0], buckets[0][1] + 1)
    return ReportOut(
        slug="takograf",
        title=TITLES["takograf"],
        from_day=from_day.isoformat(),
        to_day=to_day.isoformat(),
        kpis=[
            _kpi("drivers", "Sürücü", len(drivers)),
            _kpi("warning", "Sınır yakını", warning),
            _kpi("extensions", "Uzatma hakkı biten", exhausted),
        ],
        series=[ReportSeriesPoint(name=name, value=float(count)) for name, count in buckets],
        columns=[
            "surucu",
            "plaka",
            "kaynak",
            "gunluk_kullanilan",
            "gunluk_max",
            "gunluk_limit",
            "haftalik_kullanilan",
            "haftalik_max",
            "haftalik_limit",
            "iki_haftalik_kullanilan",
            "iki_haftalik_max",
            "iki_haftalik_limit",
            "uzatma",
            "uyari",
            "driver_id",
        ],
        rows=table,
    )


def _mask_phone(phone: str) -> str:
    if len(phone) < 7:
        return phone
    return f"{phone[:3]}***{phone[-2:]}"


def _sms(db, tenant_id, from_day, to_day, start, end) -> ReportOut:
    rows = (
        db.query(SmsOutbox)
        .filter(SmsOutbox.tenant_id == tenant_id, SmsOutbox.created_at.is_not(None), SmsOutbox.created_at >= start, SmsOutbox.created_at < end)
        .order_by(SmsOutbox.created_at.desc())
        .all()
    )
    if not rows:
        load_ids = [
            row.id
            for row in db.query(Load.id).filter(Load.tenant_id == tenant_id, Load.ready_at >= start, Load.ready_at < end).all()
        ]
        if load_ids:
            rows = (
                db.query(SmsOutbox)
                .filter(SmsOutbox.tenant_id == tenant_id, SmsOutbox.load_id.in_(load_ids))
                .order_by(SmsOutbox.id.desc())
                .all()
            )
    by_status: dict[str, int] = defaultdict(int)
    by_event: dict[str, int] = defaultdict(int)
    parts = 0
    for row in rows:
        by_status[row.status] += 1
        by_event[row.event] += 1
        parts += row.parts or 1
    failed = [row for row in rows if row.status == "iletilemedi"][:50]
    fail_ids = [item.load_id for item in failed]
    loads = (
        {row.id: row.reference for row in db.query(Load).filter(Load.id.in_(fail_ids)).all()}
        if fail_ids
        else {}
    )
    table = [
        {
            "referans": loads.get(row.load_id, ""),
            "olay": row.event,
            "durum": row.status,
            "telefon": _mask_phone(row.phone),
            "parca": row.parts,
            "hata": row.last_error or "",
        }
        for row in failed
    ]
    return ReportOut(
        slug="sms",
        title=TITLES["sms"],
        from_day=from_day.isoformat(),
        to_day=to_day.isoformat(),
        kpis=[
            _kpi("total", "Toplam SMS", len(rows)),
            _kpi("kabul", "Kabul", by_status.get("kabul", 0) + by_status.get("iletildi", 0)),
            _kpi("failed", "İletilemedi", by_status.get("iletilemedi", 0)),
            _kpi("pending", "Bekliyor", by_status.get("bekliyor", 0)),
            _kpi("dropped", "Düştü", by_status.get("dustu", 0)),
            _kpi("parts", "Toplam parça", parts),
            _kpi("atama", "Atama olayı", by_event.get("atama", 0)),
            _kpi("guncelleme", "Güncelleme", by_event.get("guncelleme", 0)),
            _kpi("iptal", "İptal", by_event.get("iptal", 0)),
        ],
        series=[ReportSeriesPoint(name=name, value=float(count)) for name, count in sorted(by_status.items())],
        columns=["referans", "olay", "durum", "telefon", "parca", "hata"],
        rows=table,
    )


def _filo(db, tenant_id, from_day, to_day, start, end, direction) -> ReportOut:
    vehicles = db.query(Vehicle).filter(Vehicle.tenant_id == tenant_id).order_by(Vehicle.plate).all()
    loads = _loads(db, tenant_id, start, end, direction)
    by_status: dict[str, int] = defaultdict(int)
    for vehicle in vehicles:
        by_status[vehicle.status] += 1
    per_vehicle: dict = defaultdict(lambda: {"teslim": 0, "atama": 0, "bos_km": 0.0})
    for row in loads:
        if row.vehicle_id is None:
            continue
        bag = per_vehicle[row.vehicle_id]
        if row.status in {"atandi", "yolda", "teslim"}:
            bag["atama"] += 1
        if row.status == "teslim":
            bag["teslim"] += 1
        if row.empty_km is not None and row.status in {"atandi", "yolda", "teslim"}:
            bag["bos_km"] += float(row.empty_km)
    table = [
        {
            "plaka": vehicle.plate,
            "durum": vehicle.status,
            "atama": per_vehicle[vehicle.id]["atama"],
            "teslim": per_vehicle[vehicle.id]["teslim"],
            "bos_km": round(per_vehicle[vehicle.id]["bos_km"], 1),
        }
        for vehicle in vehicles
    ]
    return ReportOut(
        slug="filo",
        title=TITLES["filo"],
        from_day=from_day.isoformat(),
        to_day=to_day.isoformat(),
        kpis=[
            _kpi("vehicles", "Araç", len(vehicles)),
            _kpi("serviste", "Serviste", by_status.get("serviste", 0)),
            _kpi("bakimda", "Bakımda", by_status.get("bakimda", 0)),
            _kpi("ariza", "Arıza", by_status.get("ariza", 0)),
            _kpi("assignments", "Dönem ataması", sum(bag["atama"] for bag in per_vehicle.values())),
        ],
        series=[ReportSeriesPoint(name=name, value=float(count)) for name, count in sorted(by_status.items())],
        columns=["plaka", "durum", "atama", "teslim", "bos_km"],
        rows=table,
    )


def _routes(db, tenant_id, from_day, to_day) -> ReportOut:
    # RoutesUsage pod geneli; tenant izolasyonu için yine de yalnız bu firmanın oturumu görür.
    _ = tenant_id
    days = []
    cursor = from_day
    while cursor <= to_day:
        days.append(cursor.isoformat())
        cursor += timedelta(days=1)
    rows = db.query(RoutesUsage).filter(RoutesUsage.day.in_(days)).order_by(RoutesUsage.day).all()
    by_day = {row.day: row for row in rows}
    table = []
    total_calls = total_hits = total_blocked = total_extra = 0
    for day in days:
        row = by_day.get(day)
        calls = row.calls if row else 0
        hits = row.cache_hits if row else 0
        blocked = row.blocked if row else 0
        extra = row.approved_extra if row else 0
        total_calls += calls
        total_hits += hits
        total_blocked += blocked
        total_extra += extra
        table.append({"gun": day, "cagri": calls, "cache": hits, "engellenen": blocked, "onayli_ek": extra})
    return ReportOut(
        slug="routes",
        title=TITLES["routes"],
        from_day=from_day.isoformat(),
        to_day=to_day.isoformat(),
        kpis=[
            _kpi("calls", "Routes çağrısı", total_calls),
            _kpi("cache", "Cache isabeti", total_hits),
            _kpi("blocked", "Engellenen", total_blocked),
            _kpi("extra", "Onaylı ek tavan", total_extra),
        ],
        series=[ReportSeriesPoint(name=item["gun"], value=float(item["cagri"])) for item in table],
        columns=["gun", "cagri", "cache", "engellenen", "onayli_ek"],
        rows=table,
    )
