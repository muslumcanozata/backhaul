from datetime import UTC, datetime
from decimal import Decimal
from xml.etree import ElementTree as ET

from fastapi.testclient import TestClient

from app.seyir import parse_packets, parse_tacho
from tests.helpers import auth, login
from tests.test_m2 import _vehicle


LOCATION_XML = """<?xml version="1.0"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
  <soap:Body>
    <GetActualLocationsResponse>
      <GetActualLocationsResult>
        <diffgram>
          <NewDataSet>
            <Table>
              <owner>FILO</owner>
              <device_id>1218820</device_id>
              <data_time>2022-09-05T15:03:45+03:00</data_time>
              <is_gps_active>1</is_gps_active>
              <vehicle>41 AZ 473</vehicle>
              <latitude>41.754949833333335</latitude>
              <longitude>26.853846500000003</longitude>
              <angle>36</angle>
              <speed>12</speed>
              <total_km>622512.29094120300</total_km>
              <driver_key>3996335697447020</driver_key>
              <driver>ALI YILMAZ</driver>
            </Table>
          </NewDataSet>
        </diffgram>
      </GetActualLocationsResult>
    </GetActualLocationsResponse>
  </soap:Body>
</soap:Envelope>
"""

TACHO_XML = """<?xml version="1.0"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
  <soap:Body>
    <GetDriversLastTaviStateResponse>
      <GetDriversLastTaviStateResult>
        <diffgram>
          <NewDataSet>
            <Table>
              <driver>ALI YILMAZ</driver>
              <driver_id>1</driver_id>
              <driver_code>3996335697447020</driver_code>
              <datetime_utc0>2024-07-29T06:50:50+00:00</datetime_utc0>
              <current_plate>41 AZ 473</current_plate>
              <not_used_daily_drive>576</not_used_daily_drive>
              <not_used_weekly_drive>3336</not_used_weekly_drive>
              <total_double_weekly_drive>1323</total_double_weekly_drive>
              <remaining_drive_period>296</remaining_drive_period>
              <remaining_long_drive_count>2</remaining_long_drive_count>
            </Table>
          </NewDataSet>
        </diffgram>
      </GetDriversLastTaviStateResult>
    </GetDriversLastTaviStateResponse>
  </soap:Body>
</soap:Envelope>
"""


def _firm(client: TestClient) -> str:
    admin = login(client, "admin@example.com", "admin-pass-1")
    tenant = client.post("/tenants", json={"name": "seyir-firma", "code": "seyir-firma"}, headers=auth(admin))
    assert tenant.status_code == 200, tenant.text
    created = client.post(
        f"/tenants/{tenant.json()['id']}/users",
        json={"email": "seyir@example.com", "password": "secret-pass", "role": "tenant_admin"},
        headers=auth(admin),
    )
    assert created.status_code == 200, created.text
    return login(client, "seyir@example.com", "secret-pass")


def test_parse_actual_locations_normalizes_plate_and_timezone() -> None:
    packets = parse_packets(ET.fromstring(LOCATION_XML))
    assert len(packets) == 1
    packet = packets[0]
    assert packet.plate == "41 AZ 473"
    assert packet.node == "1218820"
    assert packet.latitude == Decimal("41.754949833333335")
    assert packet.speed_kmh == Decimal("12")
    assert packet.recorded_at == datetime(2022, 9, 5, 12, 3, 45, tzinfo=UTC)
    assert packet.identity_number == "3996335697447020"


def test_parse_tacho_remaining_fields() -> None:
    rows = parse_tacho(ET.fromstring(TACHO_XML))
    assert len(rows) == 1
    assert rows[0].driver_code == "3996335697447020"
    assert rows[0].not_used_daily_drive == 576
    assert rows[0].remaining_long_drive_count == 2


def test_seyir_pull_writes_position_and_measured_tacho(shared_client: TestClient, monkeypatch) -> None:
    from datetime import timedelta

    from app.seyir import Packet

    token = _firm(shared_client)
    vehicle = shared_client.post(
        "/vehicles",
        json={"plate": "41 AZ 473", "capacity_tons": "25", "trailer_type": "tenteli", "device_id": "1218820"},
        headers=auth(token),
    )
    assert vehicle.status_code == 200, vehicle.text
    vehicle_id = vehicle.json()["id"]
    driver = shared_client.post(
        "/drivers",
        json={"name": "Ali Yılmaz", "phone": "5321112233", "card_id": "3996335697447020"},
        headers=auth(token),
    )
    assert driver.status_code == 200, driver.text
    shared_client.patch(f"/vehicles/{vehicle_id}", json={"driver_id": driver.json()["id"]}, headers=auth(token))

    shared_client.patch("/settings", json={"seyir_enabled": True}, headers=auth(token))
    saved = shared_client.put(
        "/settings/seyir",
        json={"username": "seyir-user", "password": "seyir-pass"},
        headers=auth(token),
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["seyir_configured"] is True
    assert "seyir-pass" not in saved.text

    base = parse_packets(ET.fromstring(LOCATION_XML))[0]
    fresh = Packet(
        node=base.node,
        plate=base.plate,
        latitude=base.latitude,
        longitude=base.longitude,
        speed_kmh=base.speed_kmh,
        course=base.course,
        recorded_at=datetime.now(UTC) + timedelta(minutes=1),
        odometer_km=base.odometer_km,
        driver_name=base.driver_name,
        identity_number=base.identity_number,
    )

    def fake_packets(username, password, opener=None, url: str = ""):
        assert (username, password) == ("seyir-user", "seyir-pass")
        return [fresh]

    monkeypatch.setattr("app.seyir.fetch_packets", fake_packets)
    monkeypatch.setattr("app.seyir.fetch_tacho", lambda *a, **k: parse_tacho(ET.fromstring(TACHO_XML)))

    pulled = shared_client.post("/integrations/seyir/pull", headers=auth(token))
    assert pulled.status_code == 200, pulled.text
    assert pulled.json()["updated"] == 1
    row = next(item for item in shared_client.get("/vehicles", headers=auth(token)).json() if item["id"] == vehicle_id)
    assert row["latitude"].startswith("41.754")
    assert row["tacho_source"] == "olculmus"
    assert row["tacho_daily_min"] == 0
    assert row["tacho_continuous_min"] == 0


def test_seyir_pull_blocked_when_disabled(shared_client: TestClient) -> None:
    token = _firm(shared_client)
    shared_client.put("/settings/seyir", json={"username": "u", "password": "p"}, headers=auth(token))
    blocked = shared_client.post("/integrations/seyir/pull", headers=auth(token))
    assert blocked.status_code == 409


def test_telematics_pull_runs_both_when_enabled(shared_client: TestClient, monkeypatch) -> None:
    token = _firm(shared_client)
    _vehicle(shared_client, token, "41 AZ 473", "25", "Ali Yılmaz", "5321112233", True)
    shared_client.patch("/settings", json={"seyir_enabled": True, "arvento_enabled": True}, headers=auth(token))
    shared_client.put("/settings/seyir", json={"username": "su", "password": "sp"}, headers=auth(token))
    shared_client.put("/settings/arvento", json={"username": "au", "pin1": "p1", "pin2": "p2"}, headers=auth(token))

    calls: list[str] = []

    def arvento_fetch(*args, **kwargs):
        calls.append("arvento")
        return []

    def seyir_fetch(*args, **kwargs):
        calls.append("seyir-loc")
        return []

    def seyir_tacho(*args, **kwargs):
        calls.append("seyir-tacho")
        return []

    monkeypatch.setattr("app.arvento.fetch_packets", arvento_fetch)
    monkeypatch.setattr("app.seyir.fetch_packets", seyir_fetch)
    monkeypatch.setattr("app.seyir.fetch_tacho", seyir_tacho)
    pulled = shared_client.post("/integrations/telematics/pull", headers=auth(token))
    assert pulled.status_code == 200, pulled.text
    assert calls == ["arvento", "seyir-loc", "seyir-tacho"]
