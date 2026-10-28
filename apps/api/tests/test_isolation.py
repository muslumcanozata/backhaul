from uuid import uuid4

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from tests.helpers import auth as _auth
from tests.helpers import login as _login


def test_two_tenants_cannot_read_each_others_vehicles(shared_client: TestClient) -> None:
    admin = _login(shared_client, "admin@example.com", "admin-pass-1")
    first = shared_client.post("/tenants", json={"name": "A Taşıma", "code": "a-tasima"}, headers=_auth(admin))
    second = shared_client.post("/tenants", json={"name": "B Taşıma", "code": "b-tasima"}, headers=_auth(admin))
    assert first.status_code == 200
    assert second.status_code == 200
    user_a = shared_client.post(
        f"/tenants/{first.json()['id']}/users",
        json={"email": "a@example.com", "password": "secret-pass", "role": "tenant_admin"},
        headers=_auth(admin),
    )
    user_b = shared_client.post(
        f"/tenants/{second.json()['id']}/users",
        json={"email": "b@example.com", "password": "secret-pass", "role": "tenant_admin"},
        headers=_auth(admin),
    )
    assert user_a.status_code == 200
    assert user_b.status_code == 200
    token_a = _login(shared_client, "a@example.com", "secret-pass")
    token_b = _login(shared_client, "b@example.com", "secret-pass")
    created = shared_client.post(
        "/vehicles",
        json={"plate": "34 ABC 123", "capacity_tons": "24", "trailer_type": "tenteli"},
        headers=_auth(token_a),
    )
    assert created.status_code == 200, created.text
    assert created.json()["plate"] == "34ABC123"
    own = shared_client.get("/vehicles", headers=_auth(token_a))
    other = shared_client.get("/vehicles", headers=_auth(token_b))
    assert [row["plate"] for row in own.json()] == ["34ABC123"]
    assert other.json() == []
    hidden = shared_client.post(
        f"/vehicles/{created.json()['id']}/position",
        json={"latitude": "41.0", "longitude": "29.0", "recorded_at": "2026-10-25T12:00:00Z"},
        headers=_auth(token_b),
    )
    assert hidden.status_code == 404


def test_platform_admin_cannot_open_fleet(shared_client: TestClient) -> None:
    admin = _login(shared_client, "admin@example.com", "admin-pass-1")
    response = shared_client.get("/vehicles", headers=_auth(admin))
    assert response.status_code == 403


def test_closed_trailer_type_is_rejected(shared_client: TestClient) -> None:
    admin = _login(shared_client, "admin@example.com", "admin-pass-1")
    tenant = shared_client.post("/tenants", json={"name": "A Taşıma", "code": "a-tasima"}, headers=_auth(admin))
    shared_client.post(
        f"/tenants/{tenant.json()['id']}/users",
        json={"email": "a@example.com", "password": "secret-pass", "role": "tenant_admin"},
        headers=_auth(admin),
    )
    token = _login(shared_client, "a@example.com", "secret-pass")
    response = shared_client.post(
        "/vehicles",
        json={"plate": "06 FRG 01", "capacity_tons": "25", "trailer_type": "frigolu"},
        headers=_auth(token),
    )
    assert response.status_code == 422


def test_dedicated_pod_rejects_other_tenant(tmp_path, monkeypatch) -> None:
    tenant_id = str(uuid4())
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/dedicated.db")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-value")
    monkeypatch.setenv("SECRETS_KEY", "test-secrets-key!!")
    monkeypatch.setenv("DEPLOYMENT_MODE", "dedicated")
    monkeypatch.setenv("TENANT_ID", tenant_id)
    monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "admin-pass-1")
    get_settings.cache_clear()
    with TestClient(app) as client:
        admin = _login(client, "admin@example.com", "admin-pass-1")
        foreign = client.post(
            f"/tenants/{uuid4()}/users",
            json={"email": "other@example.com", "password": "secret-pass", "role": "tenant_admin"},
            headers=_auth(admin),
        )
        assert foreign.status_code == 403
        own = client.post(
            f"/tenants/{tenant_id}/users",
            json={"email": "own@example.com", "password": "secret-pass", "role": "tenant_admin"},
            headers=_auth(admin),
        )
        assert own.status_code == 200, own.text
    get_settings.cache_clear()
