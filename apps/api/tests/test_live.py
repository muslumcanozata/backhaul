from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from tests.helpers import auth, login


def _tenant(client: TestClient, admin: str, name: str, code: str, email: str) -> str:
    tenant = client.post("/tenants", json={"name": name, "code": code}, headers=auth(admin))
    assert tenant.status_code == 200, tenant.text
    created = client.post(
        f"/tenants/{tenant.json()['id']}/users",
        json={"email": email, "password": "secret-pass", "role": "tenant_admin"},
        headers=auth(admin),
    )
    assert created.status_code == 200, created.text
    return login(client, email, "secret-pass")


def _vehicle(client: TestClient, token: str, plate: str) -> str:
    vehicle = client.post(
        "/vehicles",
        json={"plate": plate, "capacity_tons": "24", "trailer_type": "tenteli"},
        headers=auth(token),
    )
    assert vehicle.status_code == 200, vehicle.text
    return vehicle.json()["id"]


def test_live_map_receives_the_fleet_and_the_next_position(shared_client: TestClient) -> None:
    admin = login(shared_client, "admin@example.com", "admin-pass-1")
    token = _tenant(shared_client, admin, "A Taşıma", "a-tasima", "a@example.com")
    other = _tenant(shared_client, admin, "B Taşıma", "b-tasima", "b@example.com")
    vehicle_id = _vehicle(shared_client, token, "34 ABC 123")
    _vehicle(shared_client, other, "06 XYZ 789")

    with shared_client.websocket_connect(f"/live?token={token}") as socket:
        snapshot = socket.receive_json()
        assert snapshot["type"] == "snapshot"
        assert [item["plate"] for item in snapshot["vehicles"]] == ["34ABC123"]
        assert snapshot["vehicles"][0]["latitude"] is None

        posted = shared_client.post(
            f"/vehicles/{vehicle_id}/position",
            json={"latitude": "41.200", "longitude": "29.100", "speed_kmh": "62", "recorded_at": datetime.now(UTC).isoformat()},
            headers=auth(token),
        )
        assert posted.status_code == 200, posted.text
        update = socket.receive_json()
        assert update["type"] == "position"
        assert update["vehicle"]["id"] == vehicle_id
        assert update["vehicle"]["latitude"] == "41.200000"
        assert update["vehicle"]["speed_kmh"] == "62.0"

    with shared_client.websocket_connect(f"/live?token={other}") as socket:
        foreign = socket.receive_json()
        assert [item["plate"] for item in foreign["vehicles"]] == ["06XYZ789"]


def test_platform_admin_live_socket_is_refused(shared_client: TestClient) -> None:
    admin = login(shared_client, "admin@example.com", "admin-pass-1")
    with pytest.raises(WebSocketDisconnect) as caught:
        with shared_client.websocket_connect(f"/live?token={admin}") as socket:
            socket.receive_json()
    assert caught.value.code == 1008
