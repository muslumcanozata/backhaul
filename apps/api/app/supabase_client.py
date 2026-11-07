"""Supabase Auth ve Realtime Broadcast yardımcıları."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx

from app.config import BootError, Settings


class SupabaseError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def require_supabase(settings: Settings) -> None:
    """Auth ve Postgres erişilemezse BootError — süreç açılmaz."""
    if not settings.supabase_enabled:
        return
    try:
        response = httpx.get(
            f"{_base(settings)}/auth/v1/admin/users",
            headers=_headers(settings, service=True),
            params={"page": 1, "per_page": 1},
            timeout=10.0,
        )
    except Exception as exc:
        raise BootError(f"Supabase Auth'a bağlanılamadı: {exc}") from exc
    if response.status_code >= 400:
        raise BootError(f"Supabase Auth yanıt vermedi: HTTP {response.status_code}")

    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(settings.database_url, pool_pre_ping=True)
        try:
            with engine.connect() as conn:
                conn.execute(text("select 1"))
        finally:
            engine.dispose()
    except BootError:
        raise
    except Exception as exc:
        raise BootError(f"Supabase Postgres'e bağlanılamadı: {exc}") from exc


def _base(settings: Settings) -> str:
    url = (settings.supabase_url or "").rstrip("/")
    if not url:
        raise SupabaseError("SUPABASE_URL yok")
    return url


def _headers(settings: Settings, *, service: bool) -> dict[str, str]:
    key = settings.supabase_service_role_key if service else settings.supabase_anon_key
    if not key:
        raise SupabaseError("Supabase anahtarı yok")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def sign_in(settings: Settings, email: str, password: str) -> tuple[str, UUID]:
    """Parola ile giriş. (access_token, auth_user_id) döner."""
    response = httpx.post(
        f"{_base(settings)}/auth/v1/token?grant_type=password",
        headers=_headers(settings, service=False),
        json={"email": email, "password": password},
        timeout=20.0,
    )
    if response.status_code >= 400:
        raise SupabaseError("E-posta veya parola hatalı", response.status_code)
    data = response.json()
    token = data.get("access_token")
    user = data.get("user") or {}
    user_id = user.get("id")
    if not token or not user_id:
        raise SupabaseError("Supabase oturum yanıtı eksik")
    return token, UUID(user_id)


def create_auth_user(settings: Settings, email: str, password: str) -> UUID:
    response = httpx.post(
        f"{_base(settings)}/auth/v1/admin/users",
        headers=_headers(settings, service=True),
        json={
            "email": email,
            "password": password,
            "email_confirm": True,
            "app_metadata": {"provider": "backhaul"},
        },
        timeout=20.0,
    )
    if response.status_code >= 400:
        detail = response.text
        raise SupabaseError(f"Auth kullanıcısı açılamadı: {detail}", response.status_code)
    user_id = response.json().get("id")
    if not user_id:
        raise SupabaseError("Auth kullanıcısı kimliği yok")
    return UUID(user_id)


def set_auth_user_active(settings: Settings, user_id: UUID, active: bool) -> None:
    response = httpx.put(
        f"{_base(settings)}/auth/v1/admin/users/{user_id}",
        headers=_headers(settings, service=True),
        json={"ban_duration": "none" if active else "876000h"},
        timeout=20.0,
    )
    if response.status_code >= 400:
        raise SupabaseError(f"Auth kullanıcı durumu güncellenemedi: {response.text}", response.status_code)


def find_auth_user_id(settings: Settings, email: str) -> UUID | None:
    response = httpx.get(
        f"{_base(settings)}/auth/v1/admin/users",
        headers=_headers(settings, service=True),
        params={"page": 1, "per_page": 200},
        timeout=20.0,
    )
    if response.status_code >= 400:
        raise SupabaseError(f"Auth kullanıcıları okunamadı: {response.text}", response.status_code)
    for row in response.json().get("users") or []:
        if str(row.get("email", "")).lower() == email.lower():
            return UUID(row["id"])
    return None


def broadcast(settings: Settings, tenant_id: UUID, event: str, payload: dict[str, Any]) -> None:
    """Firma kanalına Realtime Broadcast gönderir. Bağlantı tutmaz."""
    topic = f"tenant:{tenant_id}"
    response = httpx.post(
        f"{_base(settings)}/realtime/v1/api/broadcast",
        headers=_headers(settings, service=True),
        json={
            "messages": [
                {
                    "topic": topic,
                    "event": event,
                    "payload": payload,
                    "private": False,
                }
            ]
        },
        timeout=10.0,
    )
    if response.status_code >= 400:
        raise SupabaseError(f"Realtime yayın başarısız: {response.text}", response.status_code)


def tenant_channel(tenant_id: UUID) -> str:
    return f"tenant:{tenant_id}"
