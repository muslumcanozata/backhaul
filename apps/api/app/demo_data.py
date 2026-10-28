"""Yerel arayüz için demo filosu. Üretim açılışında çalışmaz."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models import Alert, Driver, Load, TachoState, Tenant, User, Vehicle, VehiclePosition
from app.security import hash_password

ISTANBUL = ZoneInfo("Europe/Istanbul")

FLEET = [
    ("35IZM208", "25", "serviste", "35-1001", "Ayşe Kaya", "5322001101", "TR1001000000001", "38.423", "27.143", "72", "95", 0, 180, 420, 1800, 3200),
    ("06ANK142", "24", "serviste", "06-1002", "Mehmet Demir", "5322001102", "TR1001000000002", "39.933", "32.860", "0", "180", 0, 250, 300, 900, 2100),
    ("16BRS077", "24", "bakimda", "16-1003", "Hasan Çelik", "5322001103", "TR1001000000003", "40.188", "29.061", "0", "40", 0, 40, 90, 400, 800),
    ("41KOC019", "25", "ariza", "41-1004", "Fatma Şahin", "5322001104", "TR1001000000004", "40.803", "29.431", "0", "10", 0, 0, 40, 200, 500),
    ("01ADA303", "24", "serviste", None, None, None, None, "37.000", "35.321", "48", "120", 0, 0, 0, 0, 0),
    ("27GZT118", "25", "serviste", "27-1005", "Emre Aydın", "5322001105", "TR1001000000005", "37.066", "37.378", "0", "200", 240, 90, 510, 2400, 4100),
    ("61TRB054", "24", "serviste", "61-1006", "Zeynep Arslan", "5322001106", "TR1001000000006", "41.005", "39.726", "64", "250", 0, 120, 260, 1100, 2500),
    ("07ANT261", "25", "serviste", "07-1007", "Burak Koç", "5322001107", "TR1001000000007", "36.896", "30.713", "18", "310", 0, 70, 140, 700, 1600),
]

LOADS = [
    ("G-242", "gidis", "atandi", "35IZM208", "Ege Gıda", "İzmir", "Bornova", "38.470", "27.220", "Ankara", "Çankaya", "39.910", "32.860", "22", "28000", "412", "18", "18640"),
    ("G-243", "gidis", "planlanabilir", None, "Marmara Tekstil", "İstanbul", "Pendik", "40.877", "29.233", "Kocaeli", "Gebze", "40.803", "29.431", "12", None, None, None, None),
    ("G-244", "gidis", "planlanabilir", None, "İç Anadolu Market", "Ankara", "Çankaya", "39.910", "32.860", "Adana", "Seyhan", "37.000", "35.321", "21", None, None, None, None),
    ("G-245", "gidis", "planlanabilir", None, "Bursa Seramik", "Bursa", "Nilüfer", "40.213", "28.950", "İzmir", "Bornova", "38.470", "27.220", "18", None, None, None, None),
    ("G-246", "gidis", "planlanabilir", None, "Akdeniz Soğuk", "Antalya", "Muratpaşa", "36.888", "30.705", "Ankara", "Yenimahalle", "39.970", "32.750", "15", None, None, None, None),
    ("G-247", "gidis", "planlanabilir", None, "Karadeniz Kereste", "Trabzon", "Ortahisar", "41.005", "39.726", "İstanbul", "Pendik", "40.877", "29.233", "20", None, None, None, None),
    ("D-118", "donus", "havuz", None, "Ege Dönüş", "İzmir", "Bornova", "38.470", "27.220", "İstanbul", "Pendik", "40.877", "29.233", "18", "22000", None, None, None),
    ("D-119", "donus", "havuz", None, "Anadolu Hat", "Ankara", "Çankaya", "39.910", "32.860", "Gaziantep", "Şehitkamil", "37.066", "37.378", "20", "26500", None, None, None),
    ("D-120", "donus", "havuz", None, "Güney Navlun", "Mersin", "Yenişehir", "36.812", "34.630", "Bursa", "Nilüfer", "40.213", "28.950", "16", "14800", None, None, None),
    ("D-121", "donus", "atandi", "61TRB054", "Doğu Hat", "Adana", "Seyhan", "37.000", "35.321", "Kocaeli", "Gebze", "40.803", "29.431", "19", "17600", "640", "22", "9800"),
]

ALERTS = [
    ("35IZM208", "DAILY_DRIVING_WARNING", "uyari", 510, 540),
    ("06ANK142", "BREAK_WARNING", "uyari", 250, 270),
    ("16BRS077", "BREAK_OVERDUE", "kritik", 280, 270),
    ("27GZT118", "TACHO_ESTIMATED", "uyari", 0, 0),
    ("07ANT261", "WEEKLY_DRIVING_WARNING", "uyari", 3200, 3360),
]


def seed_demo(db: Session) -> dict[str, int]:
    tenant = db.query(Tenant).filter(Tenant.code == "a-tasima").one_or_none()
    if tenant is None:
        return {"vehicles": 0, "loads": 0, "alerts": 0}
    now = datetime.now(UTC)
    tomorrow = (datetime.now(ISTANBUL) + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
    plates = {plate: _vehicle(db, tenant.id, row, now) for row, plate in ((item, item[0]) for item in FLEET)}
    _refresh_existing(db, tenant.id, now)
    loads = 0
    for row in LOADS:
        if _load(db, tenant.id, row, plates, tomorrow):
            loads += 1
    alerts = sum(1 for row in ALERTS if _alert(db, tenant.id, row, plates))
    _viewer(db, tenant.id)
    db.commit()
    return {"vehicles": sum(1 for item in plates.values() if item), "loads": loads, "alerts": alerts}


def _vehicle(db: Session, tenant_id, row, now: datetime) -> Vehicle | None:
    plate, capacity, status, device, name, phone, card, lat, lng, speed, course, stale_min, continuous, daily, weekly, fortnight = row
    existing = db.query(Vehicle).filter(Vehicle.tenant_id == tenant_id, Vehicle.plate == plate).one_or_none()
    if existing is not None:
        return existing
    driver = None
    if name and phone:
        driver = Driver(tenant_id=tenant_id, name=name, phone=phone, card_id=card)
        db.add(driver)
        db.flush()
        db.add(
            TachoState(
                driver_id=driver.id,
                tenant_id=tenant_id,
                source="tahmini",
                continuous_min=continuous,
                daily_min=daily,
                weekly_min=weekly,
                fortnight_min=fortnight,
                day_key=now.date().isoformat(),
            )
        )
    vehicle = Vehicle(
        tenant_id=tenant_id,
        driver_id=driver.id if driver else None,
        plate=plate,
        capacity_tons=Decimal(capacity),
        trailer_type="tenteli",
        status=status,
        device_id=device,
    )
    db.add(vehicle)
    db.flush()
    db.add(
        VehiclePosition(
            vehicle_id=vehicle.id,
            latitude=Decimal(lat),
            longitude=Decimal(lng),
            speed_kmh=Decimal(speed),
            course=Decimal(course),
            recorded_at=now - timedelta(minutes=stale_min),
        )
    )
    return vehicle


def _refresh_existing(db: Session, tenant_id, now: datetime) -> None:
    vehicle = db.query(Vehicle).filter(Vehicle.tenant_id == tenant_id, Vehicle.plate == "34ABC123").one_or_none()
    if vehicle is None:
        return
    db.add(
        VehiclePosition(
            vehicle_id=vehicle.id,
            latitude=Decimal("41.015"),
            longitude=Decimal("28.976"),
            speed_kmh=Decimal("0"),
            course=Decimal("90"),
            recorded_at=now,
        )
    )


def _load(db: Session, tenant_id, row, plates: dict[str, Vehicle | None], tomorrow: datetime) -> bool:
    reference, direction, status, plate, customer, pickup_il, pickup_ilce, pickup_lat, pickup_lng, drop_il, drop_ilce, drop_lat, drop_lng, tonnage, freight, loaded_km, empty_km, benefit = row
    if db.query(Load).filter(Load.tenant_id == tenant_id, Load.reference == reference).one_or_none():
        return False
    vehicle = plates.get(plate) if plate else None
    start = tomorrow.astimezone(UTC)
    db.add(
        Load(
            tenant_id=tenant_id,
            vehicle_id=vehicle.id if vehicle else None,
            reference=reference,
            direction=direction,
            customer=customer,
            pickup_il=pickup_il,
            pickup_ilce=pickup_ilce,
            drop_il=drop_il,
            drop_ilce=drop_ilce,
            pickup_lat=Decimal(pickup_lat),
            pickup_lng=Decimal(pickup_lng),
            drop_lat=Decimal(drop_lat),
            drop_lng=Decimal(drop_lng),
            geocode_quality="yaklasik",
            tonnage=Decimal(tonnage),
            trailer_type="tenteli",
            ready_at=start,
            deliver_start=start + timedelta(hours=10),
            deliver_end=start + timedelta(hours=24),
            freight_try=Decimal(freight) if freight else None,
            status=status,
            empty_km=Decimal(empty_km) if empty_km else None,
            loaded_km=Decimal(loaded_km) if loaded_km else None,
            distance_quality="yaklasik" if loaded_km else None,
            benefit_try=Decimal(benefit) if benefit else None,
        )
    )
    return True


def _alert(db: Session, tenant_id, row, plates: dict[str, Vehicle | None]) -> bool:
    plate, code, level, measured, limit = row
    vehicle = plates.get(plate)
    if vehicle is None:
        return False
    exists = db.query(Alert).filter(Alert.tenant_id == tenant_id, Alert.vehicle_id == vehicle.id, Alert.code == code).one_or_none()
    if exists is not None:
        return False
    db.add(
        Alert(
            tenant_id=tenant_id,
            vehicle_id=vehicle.id,
            driver_id=vehicle.driver_id,
            code=code,
            level=level,
            measured=measured,
            limit_value=limit,
        )
    )
    return True


def _viewer(db: Session, tenant_id) -> None:
    if db.query(User).filter(User.email == "izleyici@example.com").one_or_none():
        return
    db.add(User(tenant_id=tenant_id, email="izleyici@example.com", password_hash=hash_password("secret-pass"), role="viewer", active=True))


if __name__ == "__main__":
    from app.config import get_settings
    from app.db import init_db

    factory = init_db(get_settings())
    with factory() as database:
        print(seed_demo(database))
