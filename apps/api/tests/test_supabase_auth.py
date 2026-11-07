from uuid import uuid4

import jwt
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.security import decode_token


def test_login_uses_supabase_token(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/sb.db")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-value")
    monkeypatch.setenv("SECRETS_KEY", "test-secrets-key!!")
    monkeypatch.setenv("DEPLOYMENT_MODE", "shared")
    monkeypatch.setenv("TELEMATICS_POLL_SECONDS", "0")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "admin-pass-1")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    get_settings.cache_clear()

    with TestClient(app) as client:
        # Yerel modda giriş hâlâ çalışır
        response = client.post("/auth/login", json={"email": "admin@example.com", "password": "admin-pass-1"})
        assert response.status_code == 200
        token = response.json()["access_token"]
        settings = get_settings()
        payload = decode_token(settings, token)
        assert payload["role"] == "platform_admin"

    get_settings.cache_clear()


def test_decode_supabase_shaped_token():
    from app.config import Settings

    secret = "supabase-jwt-secret!!"
    settings = Settings(
        deployment_mode="shared",
        jwt_secret="local-jwt-secret!!!!",
        secrets_key="test-secrets-key!!",
        database_url="postgresql+psycopg://u:p@localhost/db",
        supabase_url="https://ipmejpxeywneeaabvqmj.supabase.co",
        supabase_anon_key="anon",
        supabase_service_role_key="service",
        supabase_jwt_secret=secret,
    )
    user_id = str(uuid4())
    token = jwt.encode(
        {
            "sub": user_id,
            "role": "authenticated",
            "aud": "authenticated",
            "iss": "https://ipmejpxeywneeaabvqmj.supabase.co/auth/v1",
            "exp": 4102444800,
        },
        secret,
        algorithm="HS256",
    )
    payload = decode_token(settings, token)
    assert payload["sub"] == user_id
