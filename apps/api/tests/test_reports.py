from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.main import app
from app.models import Driver, Load, RoutesUsage, TenantSettings, Vehicle
from app.seyir import TachoPacket, apply_tacho
from tests.helpers import auth
from tests.test_m2 import _csv, _firm, _line, _vehicle


def test_operation_and_return_reports_with_delivered_at(shared_client: TestClient) -> None:
    token = _firm(shared_client)
    vehicle = _vehicle(shared_client, token, "34 AAA 1", "25", "Ali Yılmaz", "5321112233", True)
    shared_client.patch("/settings", json={"empty_km_cost": "10", "loaded_km_cost": "1", "auto_assign_estimated": True}, headers=auth(token))
    shared_client.post("/loads/import", files=_csv(_line("G-R1"), _line("D-R1", direction="donus", freight="2000")), headers=auth(token))
    loads = {item["reference"]: item for item in shared_client.get("/loads", headers=auth(token)).json()}
    assigned = shared_client.post(f"/loads/{loads['G-R1']['id']}/assign", json={"vehicle_id": vehicle}, headers=auth(token))
    assert assigned.status_code == 200, assigned.text
    with app.state.runtime.factory() as db:
        load = db.query(Load).filter(Load.reference == "G-R1").one()
        load.empty_km = Decimal("40.0")
        load.loaded_km = Decimal("100.0")
        load.distance_quality = "google"
        db.commit()
    delivered = shared_client.post(f"/loads/{loads['G-R1']['id']}/deliver", headers=auth(token))
    assert delivered.status_code == 200, delivered.text
    assert delivered.json()["delivered_at"]
    assert delivered.json()["status"] == "teslim"

    day = "2026-10-26"
    operasyon = shared_client.get(f"/reports/operasyon?from={day}&to={day}", headers=auth(token))
    assert operasyon.status_code == 200, operasyon.text
    kpis = {item["key"]: item["value"] for item in operasyon.json()["kpis"]}
    assert int(kpis["delivered"]) >= 1
    assert float(kpis["empty_km"]) >= 40

    donus = shared_client.get(f"/reports/donus-faydasi?from={day}&to={day}", headers=auth(token))
    assert donus.status_code == 200, donus.text
    assert donus.json()["title"] == "Dönüş faydası"

    exported = shared_client.get(f"/reports/operasyon/export?from={day}&to={day}", headers=auth(token))
    assert exported.status_code == 200, exported.text
    assert exported.headers["content-type"].startswith("application/vnd.openxmlformats")


def test_tacho_sms_fleet_and_routes_reports(shared_client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.netgsm.transmit", lambda *args, **kwargs: "job-report")
    token = _firm(shared_client)
    vehicle_id = _vehicle(shared_client, token, "34 BBB 2", "25", "Veli Demir", "5321112244", True)
    shared_client.put("/settings/netgsm", json={"usercode": "850", "password": "secret", "header": "FIRMAA"}, headers=auth(token))
    shared_client.post("/loads/import", files=_csv(_line("G-R2")), headers=auth(token))
    load_id = shared_client.get("/loads", headers=auth(token)).json()[0]["id"]
    shared_client.post(f"/loads/{load_id}/assign", json={"vehicle_id": vehicle_id}, headers=auth(token))

    with app.state.runtime.factory() as db:
        settings = db.query(TenantSettings).one()
        vehicle = db.get(Vehicle, UUID(vehicle_id))
        driver = db.get(Driver, vehicle.driver_id)
        driver.card_id = "CARD-R"
        apply_tacho(
            db,
            settings.tenant_id,
            [TachoPacket("Veli", "CARD-R", None, datetime.now(UTC), 30, 100, 2000, None, 20, 0)],
            settings,
        )
        day = datetime.now(ZoneInfo("Europe/Istanbul")).date().isoformat()
        usage = db.get(RoutesUsage, day)
        if usage is None:
            db.add(RoutesUsage(day=day, calls=12, cache_hits=4, approved_extra=0, blocked=1))
        else:
            usage.calls = 12
            usage.cache_hits = 4
            usage.blocked = 1
        db.commit()

    day = "2026-10-26"
    today = datetime.now(ZoneInfo("Europe/Istanbul")).date().isoformat()
    for slug in ("takograf", "sms", "filo"):
        response = shared_client.get(f"/reports/{slug}?from={day}&to={today}", headers=auth(token))
        assert response.status_code == 200, response.text
        assert response.json()["slug"] == slug
        assert response.json()["kpis"]

    routes = shared_client.get(f"/reports/routes?from={today}&to={today}", headers=auth(token)).json()
    assert {item["key"]: item["value"] for item in routes["kpis"]}["calls"] == "12"

    catalog = shared_client.get("/reports", headers=auth(token))
    assert catalog.status_code == 200
    assert len(catalog.json()) == 6
