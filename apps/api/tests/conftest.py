import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


@pytest.fixture
def shared_client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/shared.db")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-value")
    monkeypatch.setenv("SECRETS_KEY", "test-secrets-key!!")
    monkeypatch.setenv("DEPLOYMENT_MODE", "shared")
    monkeypatch.setenv("NETGSM_USERCODE", "")
    monkeypatch.setenv("ARVENTO_USERNAME", "")
    monkeypatch.setenv("GOOGLE_MAPS_SERVER_KEY", "")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "admin-pass-1")
    get_settings.cache_clear()
    with TestClient(app) as client:
        yield client
    get_settings.cache_clear()
