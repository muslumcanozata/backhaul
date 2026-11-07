import pytest

from app.config import BootError, Settings, validate_boot


def _settings(**overrides: str | None) -> Settings:
    data: dict[str, str | None] = {
        "deployment_mode": "shared",
        "jwt_secret": "test-jwt-secret-value",
        "secrets_key": "test-secrets-key!!",
        "database_url": "sqlite://",
    }
    data.update(overrides)
    return Settings(**data)


def test_shared_pod_rejects_customer_secrets() -> None:
    with pytest.raises(BootError, match="müşteri sırrı"):
        validate_boot(_settings(netgsm_usercode="8500000000"))


def test_dedicated_pod_requires_tenant_id() -> None:
    with pytest.raises(BootError, match="TENANT_ID"):
        validate_boot(_settings(deployment_mode="dedicated"))


def test_dedicated_pod_accepts_uuid() -> None:
    validate_boot(
        _settings(
            deployment_mode="dedicated",
            tenant_id="11111111-1111-1111-1111-111111111111",
            netgsm_usercode="8500000000",
        )
    )


def test_supabase_requires_keys_and_postgres() -> None:
    with pytest.raises(BootError, match="SUPABASE_ANON_KEY"):
        validate_boot(
            _settings(
                supabase_url="https://ipmejpxeywneeaabvqmj.supabase.co",
                database_url="postgresql+psycopg://u:p@localhost/db",
            )
        )
    with pytest.raises(BootError, match="Postgres"):
        validate_boot(
            _settings(
                supabase_url="https://ipmejpxeywneeaabvqmj.supabase.co",
                supabase_anon_key="anon",
                supabase_service_role_key="service",
                supabase_jwt_secret="jwt-secret-at-least-16",
                database_url="sqlite:///./x.db",
            )
        )
    validate_boot(
        _settings(
            supabase_url="https://ipmejpxeywneeaabvqmj.supabase.co",
            supabase_anon_key="anon",
            supabase_service_role_key="service",
            supabase_jwt_secret="jwt-secret-at-least-16",
            database_url="postgresql+psycopg://u:p@localhost/db",
        )
    )
