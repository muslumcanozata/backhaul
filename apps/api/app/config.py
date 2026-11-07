from functools import lru_cache
from uuid import UUID

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

CUSTOMER_SECRET_FIELDS = (
    "netgsm_usercode",
    "netgsm_password",
    "netgsm_msgheader",
    "arvento_username",
    "arvento_pin1",
    "arvento_pin2",
    "seyir_username",
    "seyir_password",
)


class BootError(RuntimeError):
    pass


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    deployment_mode: str = "shared"
    tenant_id: str | None = None
    tenant_name: str = "Firma"
    database_url: str = "sqlite:///./backhaul.db"
    jwt_secret: str = "dev-only-change-me-please"
    secrets_key: str = "dev-only-secrets-key"
    token_ttl_minutes: int = 720
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_service_role_key: str | None = None
    supabase_jwt_secret: str | None = None
    netgsm_usercode: str | None = None
    netgsm_password: str | None = None
    netgsm_msgheader: str | None = None
    arvento_username: str | None = None
    arvento_pin1: str | None = None
    arvento_pin2: str | None = None
    seyir_username: str | None = None
    seyir_password: str | None = None
    google_maps_server_key: str | None = None
    max_stops_outbound: int = 2
    max_stops_return: int = 3
    chain_candidates: int = 5
    chain_max_wait_min: int = 360
    telematics_poll_seconds: int = 30
    # Routes Matrix Essentials ücretsiz 10.000/ay → 10_000 // 30
    routes_daily_limit: int = 333

    @field_validator(
        "tenant_id",
        "bootstrap_admin_email",
        "bootstrap_admin_password",
        "google_maps_server_key",
        "supabase_url",
        "supabase_anon_key",
        "supabase_service_role_key",
        "supabase_jwt_secret",
        *CUSTOMER_SECRET_FIELDS,
        mode="before",
    )
    @classmethod
    def blank_to_none(cls, value: object) -> object:
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

    @property
    def supabase_enabled(self) -> bool:
        return bool(self.supabase_url)

    @property
    def token_secret(self) -> str:
        if self.supabase_enabled and self.supabase_jwt_secret:
            return self.supabase_jwt_secret
        return self.jwt_secret


def validate_boot(settings: Settings) -> None:
    if settings.deployment_mode not in {"shared", "dedicated"}:
        raise BootError("DEPLOYMENT_MODE shared veya dedicated olmalı")
    if len(settings.secrets_key) < 16:
        raise BootError("SECRETS_KEY en az 16 karakter olmalı")
    if settings.supabase_enabled:
        missing = [
            name
            for name, value in (
                ("SUPABASE_ANON_KEY", settings.supabase_anon_key),
                ("SUPABASE_SERVICE_ROLE_KEY", settings.supabase_service_role_key),
                ("SUPABASE_JWT_SECRET", settings.supabase_jwt_secret),
            )
            if not value
        ]
        if missing:
            raise BootError("Supabase için eksik: " + ", ".join(missing))
        if settings.database_url.startswith("sqlite"):
            raise BootError("Supabase açıkken DATABASE_URL Postgres olmalı")
    elif len(settings.jwt_secret) < 16:
        raise BootError("JWT_SECRET en az 16 karakter olmalı")
    filled = [name for name in CUSTOMER_SECRET_FIELDS if getattr(settings, name)]
    if settings.deployment_mode == "shared" and filled:
        raise BootError(
            "Paylaşılan pod müşteri sırrıyla açılmaz: " + ", ".join(filled)
        )
    if settings.deployment_mode == "dedicated":
        if not settings.tenant_id:
            raise BootError("Ayrı pod TENANT_ID ister")
        try:
            UUID(settings.tenant_id)
        except ValueError as exc:
            raise BootError("TENANT_ID UUID olmalı") from exc


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    validate_boot(settings)
    return settings
