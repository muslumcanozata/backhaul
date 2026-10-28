from fastapi.testclient import TestClient

from tests.helpers import auth as _auth
from tests.helpers import login as _login


def _firm(client: TestClient) -> tuple[str, str, str]:
    admin = _login(client, "admin@example.com", "admin-pass-1")
    tenant = client.post("/tenants", json={"name": "A Taşıma", "code": "a-tasima"}, headers=_auth(admin))
    assert tenant.status_code == 200, tenant.text
    tenant_id = tenant.json()["id"]
    created = client.post(
        f"/tenants/{tenant_id}/users",
        json={"email": "a@example.com", "password": "secret-pass", "role": "tenant_admin"},
        headers=_auth(admin),
    )
    assert created.status_code == 200, created.text
    token = _login(client, "a@example.com", "secret-pass")
    return admin, tenant_id, token


def test_roles_split_fleet_and_users(shared_client: TestClient) -> None:
    admin, tenant_id, admin_token = _firm(shared_client)
    dispatcher = shared_client.post(
        "/users",
        json={"email": "op@example.com", "password": "secret-pass", "role": "dispatcher"},
        headers=_auth(admin_token),
    )
    viewer = shared_client.post(
        "/users",
        json={"email": "iz@example.com", "password": "secret-pass", "role": "viewer"},
        headers=_auth(admin_token),
    )
    assert dispatcher.status_code == 200, dispatcher.text
    assert viewer.status_code == 200, viewer.text
    refused = shared_client.post(
        "/users",
        json={"email": "boss@example.com", "password": "secret-pass", "role": "tenant_admin"},
        headers=_auth(admin_token),
    )
    assert refused.status_code == 422

    op = _login(shared_client, "op@example.com", "secret-pass")
    look = _login(shared_client, "iz@example.com", "secret-pass")
    assert shared_client.get("/users", headers=_auth(op)).status_code == 403
    assert shared_client.get("/vehicles", headers=_auth(admin)).status_code == 403

    vehicle = shared_client.post(
        "/vehicles",
        json={"plate": "34 ABC 123", "capacity_tons": "24", "trailer_type": "tenteli"},
        headers=_auth(admin_token),
    )
    assert vehicle.status_code == 200, vehicle.text
    vehicle_id = vehicle.json()["id"]
    assert shared_client.post(
        "/vehicles",
        json={"plate": "06 DEF 456", "capacity_tons": "25", "trailer_type": "tenteli"},
        headers=_auth(op),
    ).status_code == 403
    assert shared_client.patch(f"/vehicles/{vehicle_id}", json={"status": "bakimda"}, headers=_auth(op)).status_code == 403
    position = shared_client.post(
        f"/vehicles/{vehicle_id}/position",
        json={"latitude": "41.01", "longitude": "28.97", "speed_kmh": "40", "recorded_at": "2026-10-25T18:00:00Z"},
        headers=_auth(op),
    )
    assert position.status_code == 200, position.text
    assert position.json()["recorded_at"].endswith("Z")
    assert shared_client.post(
        f"/vehicles/{vehicle_id}/position",
        json={"latitude": "41.02", "longitude": "28.98", "recorded_at": "2026-10-25T18:05:00Z"},
        headers=_auth(look),
    ).status_code == 403

    driver = shared_client.post(
        "/drivers",
        json={"name": "Ali Yılmaz", "phone": "0532 111 22 33"},
        headers=_auth(admin_token),
    )
    assert driver.status_code == 200, driver.text
    assert driver.json()["phone"] == "5321112233"
    linked = shared_client.patch(
        f"/vehicles/{vehicle_id}",
        json={"status": "serviste", "driver_id": driver.json()["id"]},
        headers=_auth(admin_token),
    )
    assert linked.status_code == 200, linked.text
    assert linked.json()["driver_id"] == driver.json()["id"]
    second = shared_client.post(
        "/vehicles",
        json={"plate": "35 GHI 789", "capacity_tons": "25", "trailer_type": "tenteli"},
        headers=_auth(admin_token),
    )
    moved = shared_client.patch(
        f"/vehicles/{second.json()['id']}",
        json={"driver_id": driver.json()["id"]},
        headers=_auth(admin_token),
    )
    assert moved.status_code == 200, moved.text
    rows = shared_client.get("/vehicles", headers=_auth(admin_token)).json()
    by_plate = {row["plate"]: row["driver_id"] for row in rows}
    assert by_plate["34ABC123"] is None
    assert by_plate["35GHI789"] == driver.json()["id"]

    closed = shared_client.patch(
        f"/users/{dispatcher.json()['id']}",
        json={"active": False},
        headers=_auth(admin_token),
    )
    assert closed.status_code == 200
    assert shared_client.post("/auth/login", json={"email": "op@example.com", "password": "secret-pass"}).status_code == 401
    listed = shared_client.get(f"/tenants/{tenant_id}/users", headers=_auth(admin))
    assert listed.status_code == 200
    assert {row["email"] for row in listed.json()} == {"a@example.com", "op@example.com", "iz@example.com"}
