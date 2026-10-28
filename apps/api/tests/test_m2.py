from datetime import UTC, datetime, timedelta
from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.arvento import Packet, fetch_packets
from tests.helpers import auth, login

HEADER = (
    "referans_no,yukleme_il,yukleme_ilce,bosaltma_il,bosaltma_ilce,tonaj,dorse_tipi,"
    "hazir_zamani,teslim_baslangic,teslim_bitis,yon,navlun_try"
)


def _firm(client: TestClient) -> str:
    admin = login(client, "admin@example.com", "admin-pass-1")
    tenant = client.post("/tenants", json={"name": "A Taşıma", "code": "a-tasima"}, headers=auth(admin))
    assert tenant.status_code == 200, tenant.text
    created = client.post(
        f"/tenants/{tenant.json()['id']}/users",
        json={"email": "a@example.com", "password": "secret-pass", "role": "tenant_admin"},
        headers=auth(admin),
    )
    assert created.status_code == 200, created.text
    return login(client, "a@example.com", "secret-pass")


def _line(reference: str, tonnage: str = "20", trailer: str = "tenteli", direction: str = "gidis", freight: str = "") -> str:
    return (
        f"{reference},İstanbul,Pendik,Ankara,Çankaya,{tonnage},{trailer},"
        f"2026-10-26 08:00,2026-10-26 18:00,2026-10-27 08:00,{direction},{freight}"
    )


def _csv(*lines: str) -> dict:
    return {"file": ("yuk.csv", (HEADER + "\n" + "\n".join(lines) + "\n").encode(), "text/csv")}


def _vehicle(client: TestClient, token: str, plate: str, capacity: str, driver: str, phone: str, fresh: bool) -> str:
    vehicle = client.post(
        "/vehicles",
        json={"plate": plate, "capacity_tons": capacity, "trailer_type": "tenteli"},
        headers=auth(token),
    )
    assert vehicle.status_code == 200, vehicle.text
    vehicle_id = vehicle.json()["id"]
    created = client.post("/drivers", json={"name": driver, "phone": phone}, headers=auth(token))
    assert created.status_code == 200, created.text
    patched = client.patch(f"/vehicles/{vehicle_id}", json={"driver_id": created.json()["id"]}, headers=auth(token))
    assert patched.status_code == 200, patched.text
    when = datetime.now(UTC) if fresh else datetime.now(UTC) - timedelta(hours=3)
    position = client.post(
        f"/vehicles/{vehicle_id}/position",
        json={"latitude": "41.015", "longitude": "28.976", "recorded_at": when.isoformat()},
        headers=auth(token),
    )
    assert position.status_code == 200, position.text
    return vehicle_id


def test_import_keeps_valid_rows_and_reports_the_rest(shared_client: TestClient) -> None:
    token = _firm(shared_client)
    result = shared_client.post(
        "/loads/import",
        files=_csv(
            _line("G-1"),
            _line("G-2", tonnage="0"),
            _line("D-1", direction="donus"),
            "Yer,Narnia,Merkez,Ankara,Çankaya,10,tenteli,2026-10-26 08:00,2026-10-26 18:00,2026-10-27 08:00,gidis,",
        ),
        headers=auth(token),
    )
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["accepted"] == 1
    assert {item["code"] for item in body["rejected"]} == {"ROW_TONNAGE", "ROW_FREIGHT", "ROW_PLACE"}
    loads = shared_client.get("/loads", headers=auth(token)).json()
    assert [item["reference"] for item in loads] == ["G-1"]
    assert loads[0]["status"] == "planlanabilir"
    assert loads[0]["geocode_quality"] == "yaklasik"

    again = shared_client.post("/loads/import", files=_csv(_line("G-1", tonnage="18")), headers=auth(token))
    assert again.json()["updated"] == 1
    assert shared_client.get("/loads", headers=auth(token)).json()[0]["tonnage"] == "18.00"


def test_assignment_rejects_capacity_trailer_and_stale_position(shared_client: TestClient) -> None:
    token = _firm(shared_client)
    small = _vehicle(shared_client, token, "34 ABC 123", "24", "Ali Yılmaz", "5321112233", True)
    stale = _vehicle(shared_client, token, "35 STALE 1", "25", "Veli Demir", "5321112244", False)
    ready = _vehicle(shared_client, token, "06 DEF 456", "25", "Ayşe Kaya", "5321112255", True)
    imported = shared_client.post(
        "/loads/import",
        files=_csv(_line("YUK-25", tonnage="25"), _line("YUK-20", tonnage="20"), _line("F-1", trailer="frigolu")),
        headers=auth(token),
    )
    assert imported.status_code == 200, imported.text
    assert any(item["code"] == "ROW_TRAILER" for item in imported.json()["rejected"])
    loads = {item["reference"]: item for item in shared_client.get("/loads", headers=auth(token)).json()}
    heavy = loads["YUK-25"]["id"]
    listed = shared_client.get(f"/loads/{heavy}/candidates", headers=auth(token))
    assert listed.status_code == 200, listed.text
    by_id = {item["vehicle_id"]: item for item in listed.json()}
    assert by_id[small]["code"] == "CAPACITY"
    assert by_id[small]["eligible"] is False
    assert by_id[stale]["code"] == "STALE_POSITION"
    assert by_id[stale]["eligible"] is False
    assert by_id[ready]["eligible"] is True
    assert by_id[ready]["distance_quality"] == "yaklasik"
    refused = shared_client.post(f"/loads/{heavy}/assign", json={"vehicle_id": small}, headers=auth(token))
    assert refused.status_code == 409
    assert refused.json()["detail"] == "CAPACITY"
    assigned = shared_client.post(f"/loads/{heavy}/assign", json={"vehicle_id": ready}, headers=auth(token))
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["status"] == "atandi"
    assert shared_client.get("/vehicles", headers=auth(token)).json()
    duties = {item["id"]: item["duty"] for item in shared_client.get("/vehicles", headers=auth(token)).json()}
    assert duties[ready] == "yuklu"

    shared_client.patch("/settings", json={"enabled_trailer_types": ["tenteli", "frigolu"]}, headers=auth(token))
    cold = shared_client.post("/loads/import", files=_csv(_line("F-1", trailer="frigolu")), headers=auth(token))
    assert cold.json()["accepted"] == 1
    cold_id = next(item["id"] for item in shared_client.get("/loads", headers=auth(token)).json() if item["reference"] == "F-1")
    trailer = shared_client.post(f"/loads/{cold_id}/assign", json={"vehicle_id": small}, headers=auth(token))
    assert trailer.status_code == 409
    assert trailer.json()["detail"] == "TRAILER"

    locked = shared_client.post("/loads/import", files=_csv(_line("YUK-25", tonnage="10")), headers=auth(token))
    assert locked.json()["rejected"][0]["code"] == "ROW_LOCKED"


def test_viewer_cannot_import_and_other_tenant_cannot_read(shared_client: TestClient) -> None:
    token = _firm(shared_client)
    viewer = shared_client.post(
        "/users",
        json={"email": "iz@example.com", "password": "secret-pass", "role": "viewer"},
        headers=auth(token),
    )
    assert viewer.status_code == 200, viewer.text
    look = login(shared_client, "iz@example.com", "secret-pass")
    assert shared_client.post("/loads/import", files=_csv(_line("G-1")), headers=auth(look)).status_code == 403
    imported = shared_client.post("/loads/import", files=_csv(_line("G-1")), headers=auth(token))
    assert imported.status_code == 200, imported.text
    load_id = shared_client.get("/loads", headers=auth(token)).json()[0]["id"]

    admin = login(shared_client, "admin@example.com", "admin-pass-1")
    other = shared_client.post("/tenants", json={"name": "B Taşıma", "code": "b-tasima"}, headers=auth(admin))
    shared_client.post(
        f"/tenants/{other.json()['id']}/users",
        json={"email": "b@example.com", "password": "secret-pass", "role": "tenant_admin"},
        headers=auth(admin),
    )
    foreign = login(shared_client, "b@example.com", "secret-pass")
    assert shared_client.get("/loads", headers=auth(foreign)).json() == []
    assert shared_client.get(f"/loads/{load_id}/candidates", headers=auth(foreign)).status_code == 404
    assert shared_client.get("/loads", headers=auth(admin)).status_code == 403


def test_file_over_two_thousand_rows_is_refused(shared_client: TestClient) -> None:
    token = _firm(shared_client)
    body = HEADER + "\n" + "\n".join(_line(f"R{index}") for index in range(2001))
    result = shared_client.post("/loads/import", files={"file": ("yuk.csv", body.encode(), "text/csv")}, headers=auth(token))
    assert result.status_code == 422
    assert result.json()["detail"] == "FILE_TOO_LARGE"


def test_xlsx_row_enters_the_queue(shared_client: TestClient) -> None:
    token = _firm(shared_client)
    book = Workbook()
    sheet = book.active
    sheet.append(HEADER.split(","))
    sheet.append(_line("X-1").split(","))
    buffer = BytesIO()
    book.save(buffer)
    result = shared_client.post(
        "/loads/import",
        files={"file": ("yuk.xlsx", buffer.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth(token),
    )
    assert result.status_code == 200, result.text
    assert result.json()["accepted"] == 1


def test_arvento_pull_matches_plate_and_hides_the_secret(shared_client: TestClient, monkeypatch) -> None:
    token = _firm(shared_client)
    vehicle_id = _vehicle(shared_client, token, "34 ABC 123", "24", "Ali Yılmaz", "5321112233", False)
    saved = shared_client.put(
        "/settings/arvento",
        json={"username": "user-1", "pin1": "pin-1", "pin2": "pin-2"},
        headers=auth(token),
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["arvento_configured"] is True
    assert "pin-1" not in saved.text

    def fake(username: str, pin1: str, pin2: str, opener=None, url: str = "") -> list[Packet]:
        assert (username, pin1, pin2) == ("user-1", "pin-1", "pin-2")
        return [
            Packet(
                node="NODE1",
                plate="34 ABC 123",
                latitude=__import__("decimal").Decimal("41.100000"),
                longitude=__import__("decimal").Decimal("29.000000"),
                speed_kmh=__import__("decimal").Decimal("18"),
                course=__import__("decimal").Decimal("90"),
                recorded_at=datetime.now(UTC),
                odometer_km=__import__("decimal").Decimal("1002.5"),
                driver_name="Ali Yılmaz",
                identity_number=None,
            )
        ]

    monkeypatch.setattr("app.arvento.fetch_packets", fake)
    pulled = shared_client.post("/integrations/arvento/pull", headers=auth(token))
    assert pulled.status_code == 200, pulled.text
    assert pulled.json()["updated"] == 1
    vehicle = next(item for item in shared_client.get("/vehicles", headers=auth(token)).json() if item["id"] == vehicle_id)
    assert vehicle["latitude"] == "41.100000"


def test_status_v4_fault_falls_back_to_v3() -> None:
    v4 = b"""<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><soap:Fault><faultstring>yok</faultstring></soap:Fault></soap:Body></soap:Envelope>"""
    v3 = """<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><GetVehicleStatusV3Response>
      <LastPacket>
        <strLicensePlate>34ABC123</strLicensePlate>
        <dLatitude>40.5</dLatitude>
        <dLongitude>29.5</dLongitude>
        <dSpeed>5</dSpeed>
        <dtGMTDateTime>2026-10-25T18:00:00</dtGMTDateTime>
        <dOdometer>10</dOdometer>
      </LastPacket>
    </GetVehicleStatusV3Response></soap:Body></soap:Envelope>""".encode()

    def opener(request, timeout=30):
        class Response:
            def read(self):
                return v4 if b"GetVehicleStatusV4" in request.data else v3

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        return Response()

    packets = fetch_packets("u", "p1", "p2", opener=opener)
    assert len(packets) == 1
    assert packets[0].plate == "34ABC123"
    assert packets[0].recorded_at == datetime(2026, 10, 25, 18, 0, tzinfo=UTC)
    assert packets[0].odometer_km == __import__("decimal").Decimal("10")
