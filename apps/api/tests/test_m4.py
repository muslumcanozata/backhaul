import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app
from app.models import Load, TachoState
from tests.helpers import auth, login
from tests.test_m2 import _csv, _line, _vehicle


def _firm(client: TestClient, code: str, email: str) -> str:
    admin = login(client, "admin@example.com", "admin-pass-1")
    tenant = client.post("/tenants", json={"name": code, "code": code}, headers=auth(admin))
    assert tenant.status_code == 200, tenant.text
    created = client.post(
        f"/tenants/{tenant.json()['id']}/users",
        json={"email": email, "password": "secret-pass", "role": "tenant_admin"},
        headers=auth(admin),
    )
    assert created.status_code == 200, created.text
    return login(client, email, "secret-pass")


def _google_leg(db, origin, destination, api_key):
    table = {
        ("41.000", "41.100"): Decimal("1.0"),
        ("41.000", "41.200"): Decimal("2.0"),
        ("42.000", "41.100"): Decimal("3.0"),
        ("42.000", "41.200"): Decimal("50.0"),
    }
    key = (f"{Decimal(origin[0]):.3f}", f"{Decimal(destination[0]):.3f}")
    kilometers = table.get(key, Decimal("1.0"))
    return kilometers, 600, "google"


def _place(reference: str, latitude: str) -> None:
    factory = app.state.runtime.factory
    with factory() as db:
        load = db.query(Load).filter(Load.reference == reference).one()
        load.pickup_lat = Decimal(latitude)
        load.pickup_lng = Decimal("29.000")
        load.drop_lat = Decimal(latitude) + Decimal("0.001")
        load.drop_lng = Decimal("29.000")
        db.commit()


def test_solver_picks_the_higher_total_not_the_greedy_pair(shared_client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.planning.road_leg", _google_leg)
    token = _firm(shared_client, "a-tasima", "a@example.com")
    near = _vehicle(shared_client, token, "34 AAA 1", "25", "Ali Yılmaz", "5321112233", True)
    far = _vehicle(shared_client, token, "06 BBB 2", "25", "Veli Demir", "5321112244", True)
    shared_client.post(
        f"/vehicles/{near}/position",
        json={"latitude": "41.000", "longitude": "29.000", "recorded_at": datetime.now(UTC).isoformat()},
        headers=auth(token),
    )
    shared_client.post(
        f"/vehicles/{far}/position",
        json={"latitude": "42.000", "longitude": "29.000", "recorded_at": datetime.now(UTC).isoformat()},
        headers=auth(token),
    )
    imported = shared_client.post(
        "/loads/import",
        files=_csv(_line("YAKIN", direction="donus", freight="1000"), _line("UZAK", direction="donus", freight="1000")),
        headers=auth(token),
    )
    assert imported.status_code == 200, imported.text
    _place("YAKIN", "41.100")
    _place("UZAK", "41.200")
    patched = shared_client.patch(
        "/settings",
        json={"empty_km_cost": "10", "loaded_km_cost": "1", "auto_assign_estimated": True},
        headers=auth(token),
    )
    assert patched.status_code == 200, patched.text
    solved = shared_client.post("/returns/solve", headers=auth(token))
    assert solved.status_code == 200, solved.text
    loads = {item["reference"]: item for item in shared_client.get("/loads", headers=auth(token)).json()}
    assert loads["YAKIN"]["vehicle_id"] == far
    assert loads["UZAK"]["vehicle_id"] == near
    assert loads["YAKIN"]["status"] == "atandi"
    assert Decimal(loads["YAKIN"]["benefit_try"]) + Decimal(loads["UZAK"]["benefit_try"]) == Decimal("1948.00")


def test_missing_cost_blocks_the_return_pool(shared_client: TestClient) -> None:
    token = _firm(shared_client, "a-tasima", "a@example.com")
    imported = shared_client.post("/loads/import", files=_csv(_line("D-1", direction="donus", freight="1000")), headers=auth(token))
    assert imported.status_code == 200, imported.text
    alerts = shared_client.get("/alerts", headers=auth(token)).json()
    assert "COST_RATES_MISSING" in {item["code"] for item in alerts}
    assert shared_client.get("/loads", headers=auth(token)).json()[0]["status"] == "havuz"


def test_netgsm_accept_locks_and_stays_on_the_firm_header(shared_client: TestClient, monkeypatch) -> None:
    calls: list[str] = []

    def transmit(usercode, password, header, phone, text, opener):
        calls.append(header)
        assert header in text or header
        assert json.dumps({"msgheader": header})
        return f"job-{header}"

    monkeypatch.setattr("app.netgsm.transmit", transmit)
    monkeypatch.setattr("app.planning.road_leg", _google_leg)
    first = _firm(shared_client, "a-tasima", "a@example.com")
    second = _firm(shared_client, "b-tasima", "b@example.com")
    for token, plate, phone, header, reference in (
        (first, "34 AAA 1", "5321112233", "FIRMAA", "A-1"),
        (second, "06 BBB 2", "5321112244", "FIRMAB", "B-1"),
    ):
        vehicle_id = _vehicle(shared_client, token, plate, "25", "Ali Yılmaz", phone, True)
        shared_client.post(
            f"/vehicles/{vehicle_id}/position",
            json={"latitude": "41.000", "longitude": "29.000", "recorded_at": datetime.now(UTC).isoformat()},
            headers=auth(token),
        )
        shared_client.post("/loads/import", files=_csv(_line(reference, direction="donus", freight="1000")), headers=auth(token))
        _place(reference, "41.100")
        saved = shared_client.put(
            "/settings/netgsm",
            json={"usercode": "850", "password": "secret", "header": header},
            headers=auth(token),
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["netgsm_configured"] is True
        shared_client.patch(
            "/settings",
            json={"empty_km_cost": "10", "loaded_km_cost": "1", "auto_assign_estimated": True},
            headers=auth(token),
        )
        solved = shared_client.post("/returns/solve", headers=auth(token))
        assert solved.status_code == 200, solved.text
        again = shared_client.post("/returns/solve", headers=auth(token))
        assert again.status_code == 200, again.text
    assert calls == ["FIRMAA", "FIRMAB"]
    for token, reference, header in ((first, "A-1", "FIRMAA"), (second, "B-1", "FIRMAB")):
        load = shared_client.get("/loads", headers=auth(token)).json()[0]
        assert load["reference"] == reference
        assert load["locked"] is True
        assert load["sms_status"] == "kabul"
        assert load["sms_job_id"] == f"job-{header}"


def test_stability_keeps_the_match_until_the_total_grows_fifteen_percent() -> None:
    from uuid import uuid4

    from app.models import TenantSettings
    from app.returns import _stable

    now = datetime.now(UTC)
    vehicle_a = uuid4()
    vehicle_b = uuid4()
    load = Load(
        id=uuid4(),
        tenant_id=uuid4(),
        reference="A",
        direction="donus",
        pickup_il="İstanbul",
        pickup_ilce="Pendik",
        drop_il="Ankara",
        drop_ilce="Çankaya",
        tonnage=Decimal("10"),
        trailer_type="tenteli",
        ready_at=now,
        deliver_start=now,
        deliver_end=now,
        status="atandi",
        vehicle_id=vehicle_a,
        benefit_try=Decimal("1000"),
    )
    settings = TenantSettings(tenant_id=load.tenant_id, stability_percent=15)
    current = (str(load.id), str(vehicle_a))
    modest = {current: 100_000, (str(load.id), str(vehicle_b)): 110_000}
    assert _stable([load], settings, modest) == [current]
    jumped = {current: 100_000, (str(load.id), str(vehicle_b)): 120_000}
    assert _stable([load], settings, jumped) == [(str(load.id), str(vehicle_b))]


def test_place_change_sends_a_single_update_sms(shared_client: TestClient, monkeypatch) -> None:
    texts: list[str] = []

    def transmit(usercode, password, header, phone, text, opener):
        texts.append(text)
        return "job-upd"

    monkeypatch.setattr("app.netgsm.transmit", transmit)
    token = _firm(shared_client, "a-tasima", "a@example.com")
    vehicle_id = _vehicle(shared_client, token, "34 AAA 1", "25", "Ali Yılmaz", "5321112233", True)
    imported = shared_client.post("/loads/import", files=_csv(_line("G-9")), headers=auth(token))
    assert imported.status_code == 200, imported.text
    load_id = shared_client.get("/loads", headers=auth(token)).json()[0]["id"]
    assigned = shared_client.post(f"/loads/{load_id}/assign", json={"vehicle_id": vehicle_id}, headers=auth(token))
    assert assigned.status_code == 200, assigned.text
    saved = shared_client.put("/settings/netgsm", json={"usercode": "850", "password": "secret", "header": "FIRMAA"}, headers=auth(token))
    assert saved.status_code == 200, saved.text
    revised = shared_client.post(f"/loads/{load_id}/revise", json={"drop_il": "Bursa", "drop_ilce": "Nilüfer"}, headers=auth(token))
    assert revised.status_code == 200, revised.text
    assert revised.json()["drop_ilce"] == "Nilüfer"
    assert sum("GUNCELLEME" in text for text in texts) == 1
    again = shared_client.post(f"/loads/{load_id}/revise", json={"drop_il": "Bursa", "drop_ilce": "Osmangazi"}, headers=auth(token))
    assert again.status_code == 200, again.text
    assert sum("GUNCELLEME" in text for text in texts) == 1


def test_delivery_report_marks_undelivered_and_keeps_the_lock(shared_client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.netgsm.transmit", lambda *args, **kwargs: "job-9")
    monkeypatch.setattr("app.netgsm._report", lambda *args, **kwargs: {"job-9": "iletilemedi"})
    token = _firm(shared_client, "a-tasima", "a@example.com")
    vehicle_id = _vehicle(shared_client, token, "34 AAA 1", "25", "Ali Yılmaz", "5321112233", True)
    shared_client.put("/settings/netgsm", json={"usercode": "850", "password": "secret", "header": "FIRMAA"}, headers=auth(token))
    shared_client.post("/loads/import", files=_csv(_line("G-8")), headers=auth(token))
    load_id = shared_client.get("/loads", headers=auth(token)).json()[0]["id"]
    assigned = shared_client.post(f"/loads/{load_id}/assign", json={"vehicle_id": vehicle_id}, headers=auth(token))
    assert assigned.json()["locked"] is True
    report = shared_client.post("/sms/report", headers=auth(token))
    assert report.status_code == 200, report.text
    body = shared_client.get("/loads", headers=auth(token)).json()[0]
    assert body["sms_status"] == "iletilemedi"
    assert body["locked"] is True
    assert "SMS_UNDELIVERED" in {item["code"] for item in shared_client.get("/alerts", headers=auth(token)).json()}


def test_delivery_frees_the_vehicle(shared_client: TestClient) -> None:
    token = _firm(shared_client, "a-tasima", "a@example.com")
    vehicle_id = _vehicle(shared_client, token, "34 AAA 1", "25", "Ali Yılmaz", "5321112233", True)
    shared_client.post("/loads/import", files=_csv(_line("G-7")), headers=auth(token))
    load_id = shared_client.get("/loads", headers=auth(token)).json()[0]["id"]
    shared_client.post(f"/loads/{load_id}/assign", json={"vehicle_id": vehicle_id}, headers=auth(token))
    delivered = shared_client.post(f"/loads/{load_id}/deliver", headers=auth(token))
    assert delivered.status_code == 200, delivered.text
    assert delivered.json()["status"] == "teslim"
    duty = {item["id"]: item["duty"] for item in shared_client.get("/vehicles", headers=auth(token)).json()}
    assert duty[vehicle_id] == "bos"


def _locked_trip(shared_client: TestClient, monkeypatch, reference: str) -> tuple[str, str, str]:
    texts: list[str] = []

    def transmit(usercode, password, header, phone, text, opener):
        texts.append(text)
        return "job-lock"

    monkeypatch.setattr("app.netgsm.transmit", transmit)
    token = _firm(shared_client, "a-tasima", "a@example.com")
    vehicle_id = _vehicle(shared_client, token, "34 AAA 1", "25", "Ali Yılmaz", "5321112233", True)
    shared_client.put("/settings/netgsm", json={"usercode": "850", "password": "secret", "header": "FIRMAA"}, headers=auth(token))
    shared_client.post("/loads/import", files=_csv(_line(reference)), headers=auth(token))
    load_id = shared_client.get("/loads", headers=auth(token)).json()[0]["id"]
    assigned = shared_client.post(f"/loads/{load_id}/assign", json={"vehicle_id": vehicle_id}, headers=auth(token))
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["locked"] is True
    assert assigned.json()["rule_pack"] == "TR-AETR-2026"
    monkeypatch.setattr("app.netgsm._texts", texts, raising=False)
    shared_client.app.state.texts = texts
    return token, vehicle_id, load_id


def test_locked_plan_breaks_when_the_day_no_longer_fits(shared_client: TestClient, monkeypatch) -> None:
    token, vehicle_id, load_id = _locked_trip(shared_client, monkeypatch, "G-6")
    texts = shared_client.app.state.texts
    factory = app.state.runtime.factory
    with factory() as db:
        state = db.query(TachoState).one()
        state.daily_min = 600
        state.extensions_used = 2
        db.commit()
    later = datetime.now(UTC) + timedelta(minutes=5)
    position = shared_client.post(
        f"/vehicles/{vehicle_id}/position",
        json={"latitude": "41.02", "longitude": "28.98", "speed_kmh": "0", "recorded_at": later.isoformat()},
        headers=auth(token),
    )
    assert position.status_code == 200, position.text
    body = shared_client.get(f"/loads/{load_id}", headers=auth(token)).json()
    assert body["status"] == "planlanabilir"
    assert body["locked"] is False
    assert body["vehicle_id"] is None
    assert any("IPTAL" in text for text in texts)


def test_breakdown_breaks_a_locked_assignment(shared_client: TestClient, monkeypatch) -> None:
    token, vehicle_id, load_id = _locked_trip(shared_client, monkeypatch, "G-5")
    texts = shared_client.app.state.texts
    patched = shared_client.patch(f"/vehicles/{vehicle_id}", json={"status": "ariza"}, headers=auth(token))
    assert patched.status_code == 200, patched.text
    body = shared_client.get(f"/loads/{load_id}", headers=auth(token)).json()
    assert body["status"] == "planlanabilir"
    assert body["vehicle_id"] is None
    assert any("IPTAL" in text for text in texts)


def test_undelivered_sms_can_be_sent_again(shared_client: TestClient, monkeypatch) -> None:
    calls = {"n": 0}

    def transmit(usercode, password, header, phone, text, opener):
        calls["n"] += 1
        return f"job-{calls['n']}"

    monkeypatch.setattr("app.netgsm.transmit", transmit)
    monkeypatch.setattr("app.netgsm._report", lambda *args, **kwargs: {"job-1": "iletilemedi"})
    token = _firm(shared_client, "a-tasima", "a@example.com")
    vehicle_id = _vehicle(shared_client, token, "34 AAA 1", "25", "Ali Yılmaz", "5321112233", True)
    shared_client.put("/settings/netgsm", json={"usercode": "850", "password": "secret", "header": "FIRMAA"}, headers=auth(token))
    shared_client.post("/loads/import", files=_csv(_line("G-4")), headers=auth(token))
    load_id = shared_client.get("/loads", headers=auth(token)).json()[0]["id"]
    shared_client.post(f"/loads/{load_id}/assign", json={"vehicle_id": vehicle_id}, headers=auth(token))
    shared_client.post("/sms/report", headers=auth(token))
    resent = shared_client.post(f"/loads/{load_id}/sms/resend", headers=auth(token))
    assert resent.status_code == 200, resent.text
    assert calls["n"] == 2
    assert resent.json()["sms_status"] == "kabul"
