from datetime import UTC, datetime, timedelta
from decimal import Decimal
from xml.etree import ElementTree as ET

from fastapi.testclient import TestClient

from app.seyir import Packet, parse_packets
from tests.helpers import auth, login


LOCATION_WITH_FUEL = """<?xml version="1.0"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
  <soap:Body>
    <GetActualLocationsResponse>
      <GetActualLocationsResult>
        <diffgram>
          <NewDataSet>
            <Table>
              <device_id>1218820</device_id>
              <data_time>2026-11-01T12:00:00+03:00</data_time>
              <vehicle>34 ABC 1</vehicle>
              <latitude>41.0</latitude>
              <longitude>29.0</longitude>
              <speed>10</speed>
              <total_km>1000</total_km>
              <driver_key>CARD-D</driver_key>
              <driver>Ali Yilmaz</driver>
              <fuel_level>40</fuel_level>
            </Table>
          </NewDataSet>
        </diffgram>
      </GetActualLocationsResult>
    </GetActualLocationsResponse>
  </soap:Body>
</soap:Envelope>
"""


def _firm(client: TestClient) -> str:
    admin = login(client, "admin@example.com", "admin-pass-1")
    tenant = client.post("/tenants", json={"name": "ozluk-firma", "code": "ozluk-firma"}, headers=auth(admin))
    assert tenant.status_code == 200, tenant.text
    created = client.post(
        f"/tenants/{tenant.json()['id']}/users",
        json={"email": "ozluk@example.com", "password": "secret-pass", "role": "tenant_admin"},
        headers=auth(admin),
    )
    assert created.status_code == 200, created.text
    return login(client, "ozluk@example.com", "secret-pass")


def _vehicle_ready(client: TestClient, token: str) -> tuple[str, str]:
    vehicle = client.post(
        "/vehicles",
        json={"plate": "34 ABC 1", "capacity_tons": "25", "trailer_type": "tenteli", "device_id": "1218820"},
        headers=auth(token),
    )
    assert vehicle.status_code == 200, vehicle.text
    driver = client.post(
        "/drivers",
        json={"name": "Ali Yilmaz", "phone": "5321112233", "card_id": "CARD-D"},
        headers=auth(token),
    )
    assert driver.status_code == 200, driver.text
    patched = client.patch(f"/vehicles/{vehicle.json()['id']}", json={"driver_id": driver.json()["id"]}, headers=auth(token))
    assert patched.status_code == 200, patched.text
    return vehicle.json()["id"], driver.json()["id"]


def test_manual_dossier_entries_and_summary(shared_client: TestClient) -> None:
    token = _firm(shared_client)
    vehicle_id, driver_id = _vehicle_ready(shared_client, token)
    when = datetime.now(UTC).isoformat()

    maint = shared_client.post(
        f"/vehicles/{vehicle_id}/maintenances",
        json={"kind": "periyodik", "happened_at": when, "odometer_km": "1200", "cost_try": "3500", "workshop": "Ordu Servis"},
        headers=auth(token),
    )
    assert maint.status_code == 200, maint.text

    tire = shared_client.post(
        f"/vehicles/{vehicle_id}/tire-events",
        json={"position": "FL", "event": "degisti", "brand_size": "315/70R22.5", "happened_at": when, "odometer_km": "1200"},
        headers=auth(token),
    )
    assert tire.status_code == 200, tire.text

    fuel = shared_client.post(
        f"/vehicles/{vehicle_id}/fuel-fills",
        json={"happened_at": when, "liters": "400", "amount_try": "18000", "odometer_km": "1200", "station": "Shell"},
        headers=auth(token),
    )
    assert fuel.status_code == 200, fuel.text

    dossier = shared_client.get(f"/vehicles/{vehicle_id}/dossier", headers=auth(token))
    assert dossier.status_code == 200, dossier.text
    body = dossier.json()
    assert body["plate"].replace(" ", "") == "34ABC1"
    assert body["driver_id"] == driver_id
    assert len(body["maintenances"]) == 1
    assert len(body["tire_events"]) == 1
    assert len(body["fuel_fills"]) == 1
    assert len(body["driver_stints"]) >= 1
    assert body["driver_stints"][0]["ended_at"] is None


def test_viewer_cannot_write_dossier(shared_client: TestClient) -> None:
    token = _firm(shared_client)
    vehicle_id, _ = _vehicle_ready(shared_client, token)
    admin = login(shared_client, "admin@example.com", "admin-pass-1")
    tenants = shared_client.get("/tenants", headers=auth(admin)).json()
    tenant_id = next(item["id"] for item in tenants if item["code"] == "ozluk-firma")
    shared_client.post(
        f"/tenants/{tenant_id}/users",
        json={"email": "izle@example.com", "password": "secret-pass", "role": "viewer"},
        headers=auth(admin),
    )
    viewer = login(shared_client, "izle@example.com", "secret-pass")
    blocked = shared_client.post(
        f"/vehicles/{vehicle_id}/fuel-fills",
        json={"happened_at": datetime.now(UTC).isoformat(), "liters": "10"},
        headers=auth(viewer),
    )
    assert blocked.status_code == 403
    ok = shared_client.get(f"/vehicles/{vehicle_id}/dossier", headers=auth(viewer))
    assert ok.status_code == 200


def test_seyir_fuel_sample_and_auto_fill(shared_client: TestClient, monkeypatch) -> None:
    token = _firm(shared_client)
    vehicle_id, _ = _vehicle_ready(shared_client, token)
    shared_client.patch("/settings", json={"seyir_enabled": True}, headers=auth(token))
    shared_client.put("/settings/seyir", json={"username": "u", "password": "p"}, headers=auth(token))

    base = parse_packets(ET.fromstring(LOCATION_WITH_FUEL))[0]
    assert base.fuel_level_pct == Decimal("40")
    first = Packet(
        node=base.node,
        plate=base.plate,
        latitude=base.latitude,
        longitude=base.longitude,
        speed_kmh=base.speed_kmh,
        course=base.course,
        recorded_at=datetime.now(UTC),
        odometer_km=base.odometer_km,
        driver_name=base.driver_name,
        identity_number=base.identity_number,
        fuel_level_pct=Decimal("40"),
        fuel_level_liters=None,
    )
    second = Packet(
        node=base.node,
        plate=base.plate,
        latitude=base.latitude,
        longitude=base.longitude,
        speed_kmh=base.speed_kmh,
        course=base.course,
        recorded_at=datetime.now(UTC) + timedelta(minutes=2),
        odometer_km=Decimal("1010"),
        driver_name=base.driver_name,
        identity_number=base.identity_number,
        fuel_level_pct=Decimal("55"),
        fuel_level_liters=None,
    )
    queue = {"packets": [first]}

    def fake_packets(*args, **kwargs):
        return queue["packets"]

    monkeypatch.setattr("app.seyir.fetch_packets", fake_packets)
    monkeypatch.setattr("app.seyir.fetch_tacho", lambda *a, **k: [])
    assert shared_client.post("/integrations/seyir/pull", headers=auth(token)).status_code == 200
    queue["packets"] = [second]
    assert shared_client.post("/integrations/seyir/pull", headers=auth(token)).status_code == 200

    samples = shared_client.get(f"/vehicles/{vehicle_id}/fuel-samples", headers=auth(token))
    assert samples.status_code == 200
    assert len(samples.json()) >= 2
    dossier = shared_client.get(f"/vehicles/{vehicle_id}/dossier", headers=auth(token)).json()
    seyir_fills = [row for row in dossier["fuel_fills"] if row["source"] == "seyir"]
    assert seyir_fills
    assert "Depo" in (seyir_fills[0]["note"] or "")
