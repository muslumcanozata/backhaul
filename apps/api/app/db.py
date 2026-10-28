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
        return create_engine(database_url)
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
    }
    load_columns = {
        "planned_drive_min": "INTEGER",
        "planned_break_min": "INTEGER",
        "calculated_at": "DATETIME",
        "uses_extension": "BOOLEAN DEFAULT 0",
        "benefit_try": "NUMERIC(14, 2)",
        "locked": "BOOLEAN DEFAULT 0",
        "broker_firm": "VARCHAR(200)",
    }
    secret_columns = {
        "netgsm_usercode": "VARCHAR(500)",
        "netgsm_password": "VARCHAR(500)",
        "netgsm_msgheader": "VARCHAR(500)",
    }
    with bind.connect() as conn:
        _add_missing(conn, "tenant_settings", settings_columns)
        _add_missing(conn, "loads", load_columns)
        _add_missing(conn, "tenant_secrets", secret_columns)
        conn.commit()


def _add_missing(conn, table: str, columns: dict[str, str]) -> None:
    rows = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
    names = {row[1] for row in rows}
    if not names:
        return
    for column, ddl in columns.items():
        if column not in names:
            conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def _ensure_dedicated_tenant(factory: sessionmaker[Session], settings: Settings) -> None:
    from app.models import Tenant, TenantSettings

    tenant_id = UUID(settings.tenant_id or "")
    with factory() as db:
        if db.get(Tenant, tenant_id) is None:
            db.add(Tenant(id=tenant_id, name=settings.tenant_name, code="pod"))
            db.add(TenantSettings(tenant_id=tenant_id))
            db.commit()


def _ensure_bootstrap_admin(factory: sessionmaker[Session], settings: Settings) -> None:
    from app.models import User
    from app.security import hash_password

    if not settings.bootstrap_admin_email or not settings.bootstrap_admin_password:
        return
    with factory() as db:
        exists = db.query(User).filter(User.email == settings.bootstrap_admin_email).one_or_none()
        if exists is None:
            db.add(
                User(
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
