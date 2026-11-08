from collections.abc import Generator
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings


class Base(DeclarativeBase):
    pass


def make_engine(database_url: str):
    if not database_url.startswith("sqlite"):
        # Supabase transaction pooler (6543) ile hazırlıklı ifade kullanma.
        return create_engine(
            database_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            pool_recycle=300,
            # Transaction pooler (6543) aynı prepared statement adını ikinci bağlantıda reddeder.
            connect_args={"prepare_threshold": None},
        )
    # Bellek veritabanı tek bağlantıda kalır. Dosya veritabanı eşzamanlı istekte
    # ayrı bağlantı kullanır; tek bağlantı satırları birbirine karıştırır.
    memory = database_url in {"sqlite://", "sqlite:///:memory:"} or ":memory:" in database_url
    options: dict = {"connect_args": {"check_same_thread": False}}
    if memory:
        options["poolclass"] = StaticPool
    return create_engine(database_url, **options)


def make_session_factory(database_url: str) -> sessionmaker[Session]:
    return sessionmaker(bind=make_engine(database_url), autoflush=False, expire_on_commit=False)


def init_db(settings: Settings) -> sessionmaker[Session]:
    from app import models  # noqa: F401

    factory = make_session_factory(settings.database_url)
    bind = factory.kw["bind"]
    Base.metadata.create_all(bind)
    _ensure_vehicle_driver_column(bind)
    _ensure_position_columns(bind)
    _ensure_tacho_columns(bind)
    _ensure_tacho_state_columns(bind)
    _ensure_list_indexes(bind)
    if settings.deployment_mode == "dedicated":
        _ensure_dedicated_tenant(factory, settings)
    _ensure_bootstrap_admin(factory, settings)
    return factory


def _ensure_vehicle_driver_column(bind) -> None:
    if bind.dialect.name != "sqlite":
        return
    with bind.connect() as conn:
        rows = conn.exec_driver_sql("PRAGMA table_info(vehicles)").fetchall()
        names = {row[1] for row in rows}
        if names and "driver_id" not in names:
            conn.exec_driver_sql("ALTER TABLE vehicles ADD COLUMN driver_id VARCHAR(36)")
            conn.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS uq_vehicle_driver ON vehicles (driver_id)")
            conn.commit()


def _ensure_position_columns(bind) -> None:
    if bind.dialect.name != "sqlite":
        return
    with bind.connect() as conn:
        rows = conn.exec_driver_sql("PRAGMA table_info(vehicle_positions)").fetchall()
        names = {row[1] for row in rows}
        if not names:
            return
        if "course" not in names:
            conn.exec_driver_sql("ALTER TABLE vehicle_positions ADD COLUMN course NUMERIC(6, 1)")
        if "odometer_km" not in names:
            conn.exec_driver_sql("ALTER TABLE vehicle_positions ADD COLUMN odometer_km NUMERIC(12, 1)")
        conn.commit()


def _ensure_tacho_columns(bind) -> None:
    if bind.dialect.name != "sqlite":
        return
    settings_columns = {
        "tacho_continuous_min": "INTEGER DEFAULT 270",
        "tacho_daily_min": "INTEGER DEFAULT 540",
        "tacho_extended_min": "INTEGER DEFAULT 600",
        "tacho_extensions": "INTEGER DEFAULT 2",
        "tacho_weekly_min": "INTEGER DEFAULT 3360",
        "tacho_fortnight_min": "INTEGER DEFAULT 5400",
        "tacho_warning_min": "INTEGER DEFAULT 30",
        "return_approval": "BOOLEAN DEFAULT 0",
        "stability_percent": "INTEGER DEFAULT 15",
        "reject_negative_benefit": "BOOLEAN DEFAULT 0",
        "auto_assign_estimated": "BOOLEAN DEFAULT 0",
        "arvento_enabled": "BOOLEAN DEFAULT 0",
        "seyir_enabled": "BOOLEAN DEFAULT 0",
        "home_base_il": "VARCHAR(80)",
        "home_base_ilce": "VARCHAR(80)",
        "toll_enabled": "BOOLEAN DEFAULT 0",
        "planning_fingerprint": "VARCHAR(64)",
    }
    load_columns = {
        "planned_drive_min": "INTEGER",
        "planned_break_min": "INTEGER",
        "calculated_at": "DATETIME",
        "uses_extension": "BOOLEAN DEFAULT 0",
        "benefit_try": "NUMERIC(14, 2)",
        "locked": "BOOLEAN DEFAULT 0",
        "broker_firm": "VARCHAR(200)",
        "toll_try": "NUMERIC(12, 2)",
        "base_km": "NUMERIC(8, 1)",
        "chain_value_try": "NUMERIC(14, 2)",
        "chain_note": "VARCHAR(500)",
        "driver_advice": "VARCHAR(500)",
        "delivered_at": "DATETIME",
    }
    road_columns = {
        "toll_try": "NUMERIC(12, 2)",
        "toll_state": "VARCHAR(12)",
        "fetched_at": "DATETIME",
        "tries": "INTEGER DEFAULT 0",
    }
    secret_columns = {
        "netgsm_usercode": "VARCHAR(500)",
        "netgsm_password": "VARCHAR(500)",
        "netgsm_msgheader": "VARCHAR(500)",
        "seyir_username": "VARCHAR(500)",
        "seyir_password": "VARCHAR(500)",
    }
    with bind.connect() as conn:
        _add_missing(conn, "tenant_settings", settings_columns)
        _add_missing(conn, "loads", load_columns)
        _add_missing(conn, "road_cache", road_columns)
        _add_missing(conn, "tenant_secrets", secret_columns)
        _add_missing(conn, "sms_outbox", {"created_at": "DATETIME"})
        conn.commit()


def _add_missing(conn, table: str, columns: dict[str, str]) -> None:
    rows = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
    names = {row[1] for row in rows}
    if not names:
        return
    for column, ddl in columns.items():
        if column not in names:
            conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def _ensure_tacho_state_columns(bind) -> None:
    columns = {
        "activity_status": "VARCHAR(40)",
        "daily_rest_remain_min": "INTEGER",
        "weekly_rest_remain_min": "INTEGER",
    }
    with bind.connect() as conn:
        if bind.dialect.name == "sqlite":
            _add_missing(conn, "tacho_states", columns)
            conn.commit()
            return
        if bind.dialect.name != "postgresql":
            return
        existing = {
            row[0]
            for row in conn.exec_driver_sql(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = current_schema() AND table_name = 'tacho_states'"
            ).fetchall()
        }
        if not existing:
            return
        for column, ddl in columns.items():
            if column not in existing:
                conn.exec_driver_sql(f"ALTER TABLE tacho_states ADD COLUMN {column} {ddl}")
        conn.commit()


def _ensure_list_indexes(bind) -> None:
    statements = [
        "CREATE INDEX IF NOT EXISTS ix_vehicle_positions_vehicle_recorded ON vehicle_positions (vehicle_id, recorded_at DESC)",
        "CREATE INDEX IF NOT EXISTS ix_tacho_samples_driver_recorded ON tacho_samples (driver_id, recorded_at DESC)",
        "CREATE INDEX IF NOT EXISTS ix_loads_vehicle_status ON loads (vehicle_id, status)",
    ]
    with bind.connect() as conn:
        for statement in statements:
            conn.exec_driver_sql(statement)
        conn.commit()


def _ensure_dedicated_tenant(factory: sessionmaker[Session], settings: Settings) -> None:
    from app.models import Tenant, TenantSettings

    tenant_id = UUID(settings.tenant_id or "")
    with factory() as db:
        if db.get(Tenant, tenant_id) is None:
            db.add(Tenant(id=tenant_id, name=settings.tenant_name, code="pod"))
            db.add(TenantSettings(tenant_id=tenant_id))
            db.commit()


def _ensure_bootstrap_admin(factory: sessionmaker[Session], settings: Settings) -> None:
    from uuid import uuid4

    from app.models import User
    from app.security import hash_password
    from app.supabase_client import SupabaseError, create_auth_user, find_auth_user_id

    if not settings.bootstrap_admin_email or not settings.bootstrap_admin_password:
        return
    with factory() as db:
        exists = db.query(User).filter(User.email == settings.bootstrap_admin_email).one_or_none()
        if exists is not None:
            return
        if settings.supabase_enabled:
            try:
                auth_id = find_auth_user_id(settings, settings.bootstrap_admin_email)
                if auth_id is None:
                    auth_id = create_auth_user(
                        settings,
                        settings.bootstrap_admin_email,
                        settings.bootstrap_admin_password,
                    )
            except SupabaseError as exc:
                raise RuntimeError(str(exc)) from exc
            db.add(
                User(
                    id=auth_id,
                    email=settings.bootstrap_admin_email,
                    password_hash=None,
                    role="platform_admin",
                )
            )
        else:
            db.add(
                User(
                    id=uuid4(),
                    email=settings.bootstrap_admin_email,
                    password_hash=hash_password(settings.bootstrap_admin_password),
                    role="platform_admin",
                )
            )
        db.commit()


def session_scope(factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    db = factory()
    try:
        yield db
    finally:
        db.close()
