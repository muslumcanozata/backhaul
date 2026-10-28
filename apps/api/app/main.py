import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import BootError, get_settings
from app.db import init_db
from app.deps import AppState, get_state
from app.live import hub
from app.routers import alerts, auth, fleet, live, loads, tenants, users

log = logging.getLogger("backhaul.sms")


def build_state() -> AppState:
    settings = get_settings()
    factory = init_db(settings)
    return AppState(settings=settings, factory=factory)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.state.runtime = build_state()
    except BootError as exc:
        raise RuntimeError(str(exc)) from exc
    hub.bind(asyncio.get_running_loop())
    reports = asyncio.create_task(_report_loop(app))
    yield
    reports.cancel()
    try:
        await reports
    except asyncio.CancelledError:
        pass


async def _report_loop(app: FastAPI) -> None:
    while True:
        try:
            await asyncio.sleep(180)
            await asyncio.to_thread(_poll_saved, app.state.runtime)
        except asyncio.CancelledError:
            return
        except Exception:
            log.exception("İletim raporu okunamadı")


def _poll_saved(runtime: AppState) -> None:
    from app.models import SmsOutbox
    from app.netgsm import poll_reports

    with runtime.factory() as db:
        tenant_ids = [row[0] for row in db.query(SmsOutbox.tenant_id).filter(SmsOutbox.status == "kabul").distinct()]
        for tenant_id in tenant_ids:
            poll_reports(db, tenant_id, runtime.settings)
        db.commit()


def create_app() -> FastAPI:
    app = FastAPI(title="Backhaul", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def state_dependency() -> AppState:
        return app.state.runtime

    app.dependency_overrides[get_state] = state_dependency
    app.include_router(auth.router)
    app.include_router(tenants.router)
    app.include_router(fleet.router)
    app.include_router(users.router)
    app.include_router(loads.router)
    app.include_router(alerts.router)
    app.include_router(live.router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
