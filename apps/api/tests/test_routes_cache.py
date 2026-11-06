import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient

from app.geo import approve_extra, road_leg, usage_snapshot
from app.main import app
from app.models import RoadCache
from tests.test_chain import _Reply


def _ok(request, timeout):
    return _Reply([{"condition": "ROUTE_EXISTS", "distanceMeters": 50000, "duration": "1800s"}])


def _db():
    return app.state.runtime.factory()


def test_same_leg_is_served_from_cache(shared_client: TestClient) -> None:
    calls = []

    def opener(request, timeout):
        calls.append(1)
        return _ok(request, timeout)

    origin, dest = (Decimal("39.100"), Decimal("35.200")), (Decimal("38.400"), Decimal("27.100"))
    with _db() as db:
        first = road_leg(db, origin, dest, "test-key", opener, limit=20)
        second = road_leg(db, origin, dest, "test-key", opener, limit=20)
        usage = usage_snapshot(db, 20)
        assert first == second
        assert first[2] == "google"
        assert len(calls) == 1
        assert usage["routes_today"] == 1
        assert usage["routes_cache_hits"] == 1


def test_vehicle_move_inside_five_km_hits_the_same_cell(shared_client: TestClient) -> None:
    calls = []

    def opener(request, timeout):
        calls.append(json.loads(request.data.decode()))
        return _ok(request, timeout)

    dest = (Decimal("38.400"), Decimal("27.100"))
    with _db() as db:
        road_leg(db, (Decimal("41.000"), Decimal("29.000")), dest, "test-key", opener, origin_coarse=True, limit=20)
        road_leg(db, (Decimal("41.020"), Decimal("29.010")), dest, "test-key", opener, origin_coarse=True, limit=20)
        assert len(calls) == 1
        sent = calls[0]["origins"][0]["waypoint"]["location"]["latLng"]
        assert sent["latitude"] == 41.0
        assert sent["longitude"] == 29.0


def test_approximate_is_retried_after_backoff(shared_client: TestClient) -> None:
    calls = []

    def opener(request, timeout):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("down")
        return _ok(request, timeout)

    origin, dest = (Decimal("37.000"), Decimal("35.300")), (Decimal("36.800"), Decimal("30.700"))
    start = datetime(2026, 11, 1, 10, 0, tzinfo=UTC)
    with _db() as db:
        first = road_leg(db, origin, dest, "test-key", opener, limit=20, now=start)
        assert first[2] == "yaklasik"
        second = road_leg(db, origin, dest, "test-key", opener, limit=20, now=start + timedelta(minutes=2))
        assert second[2] == "yaklasik"
        third = road_leg(db, origin, dest, "test-key", opener, limit=20, now=start + timedelta(minutes=16))
        assert third[2] == "google"
        assert len(calls) == 2


def test_daily_limit_blocks_then_approval_unlocks(shared_client: TestClient) -> None:
    calls = []

    def opener(request, timeout):
        calls.append(1)
        return _ok(request, timeout)

    a = (Decimal("40.000"), Decimal("32.800"))
    b = (Decimal("39.900"), Decimal("32.850"))
    c = (Decimal("39.800"), Decimal("32.900"))
    d = (Decimal("39.700"), Decimal("32.950"))
    dest = (Decimal("38.400"), Decimal("27.100"))
    with _db() as db:
        assert road_leg(db, a, dest, "test-key", opener, limit=2)[2] == "google"
        assert road_leg(db, b, dest, "test-key", opener, limit=2)[2] == "google"
        blocked = road_leg(db, c, dest, "test-key", opener, limit=2)
        assert blocked[2] == "yaklasik"
        usage = usage_snapshot(db, 2)
        assert usage["routes_today"] == 2
        assert usage["routes_needs_approval"] is True
        assert usage["routes_blocked"] == 1
        assert db.get(RoadCache, f"{a[0]:.3f}|{a[1]:.3f}|{dest[0]:.3f}|{dest[1]:.3f}") is not None
        approve_extra(db, extra=2)
        unlocked = road_leg(db, d, dest, "test-key", opener, limit=2)
        assert unlocked[2] == "google"
        after = usage_snapshot(db, 2)
        assert after["routes_needs_approval"] is False
        assert after["routes_allowed"] == 4
        assert after["routes_today"] == 3
        assert len(calls) == 3


def test_memo_counts_a_blocked_leg_once(shared_client: TestClient) -> None:
    calls = []

    def opener(request, timeout):
        calls.append(1)
        return _ok(request, timeout)

    origin, dest = (Decimal("36.200"), Decimal("36.150")), (Decimal("37.000"), Decimal("35.300"))
    memo: dict = {}
    with _db() as db:
        road_leg(db, origin, dest, "test-key", opener, limit=1, memo=memo)
        road_leg(db, origin, dest, "test-key", opener, limit=1, memo=memo)
        other = (Decimal("36.300"), Decimal("36.200"))
        road_leg(db, other, dest, "test-key", opener, limit=1, memo=memo)
        road_leg(db, other, dest, "test-key", opener, limit=1, memo=memo)
        usage = usage_snapshot(db, 1)
        assert len(calls) == 1
        assert usage["routes_blocked"] == 1
        assert usage["routes_needs_approval"] is True


def test_solve_skips_when_the_five_km_cell_is_unchanged(shared_client: TestClient, monkeypatch) -> None:
    from app.models import TenantSettings, VehiclePosition
    from app.planning import candidates
    from app.returns import solve_returns
    from tests.helpers import auth
    from tests.test_chain import _leg_ten, _setup_pool
    from tests.test_m4 import _firm

    monkeypatch.setattr("app.planning.road_leg", _leg_ten)
    token = _firm(shared_client, "a-tasima", "a@example.com")
    vehicle = _setup_pool(shared_client, token)
    shared_client.patch("/settings", json={"empty_km_cost": "10", "loaded_km_cost": "1", "auto_assign_estimated": True}, headers=auth(token))
    seen = {"n": 0}

    def wrapped(*args, **kwargs):
        seen["n"] += 1
        return candidates(*args, **kwargs)

    monkeypatch.setattr("app.returns.candidates", wrapped)
    with _db() as db:
        settings = db.query(TenantSettings).one()
        runtime = app.state.runtime.settings
        assert solve_returns(db, settings.tenant_id, settings, "k", runtime) == 0
        assert seen["n"] == 0
        position = (
            db.query(VehiclePosition)
            .filter(VehiclePosition.vehicle_id == UUID(vehicle))
            .order_by(VehiclePosition.recorded_at.desc())
            .first()
        )
        assert position is not None
        position.latitude = Decimal("41.100")
        position.recorded_at = datetime.now(UTC)
        db.flush()
        solve_returns(db, settings.tenant_id, settings, "k", runtime)
        moved = seen["n"]
        assert moved >= 1
        solve_returns(db, settings.tenant_id, settings, "k", runtime)
        assert seen["n"] == moved
        solve_returns(db, settings.tenant_id, settings, "k", runtime, force=True)
        assert seen["n"] > moved


def test_confirm_lock_uses_the_live_point(shared_client: TestClient, monkeypatch) -> None:
    from app.models import Load, TenantSettings, VehiclePosition
    from app.planning import confirm_lock
    from tests.test_chain import _setup_pool
    from tests.test_m4 import _firm

    seen = []

    def fake(db, origin, destination, api_key, tolls=False, origin_coarse=False, **_):
        seen.append((origin, origin_coarse))
        return Decimal("12.0"), 700, "google"

    monkeypatch.setattr("app.planning.road_leg", fake)
    token = _firm(shared_client, "a-tasima", "a@example.com")
    vehicle = _setup_pool(shared_client, token)
    with _db() as db:
        load = db.query(Load).filter(Load.reference == "A").one()
        load.vehicle_id = UUID(vehicle)
        load.status = "atandi"
        load.loaded_km = Decimal("10")
        position = (
            db.query(VehiclePosition)
            .filter(VehiclePosition.vehicle_id == UUID(vehicle))
            .order_by(VehiclePosition.recorded_at.desc())
            .first()
        )
        assert position is not None
        position.latitude = Decimal("41.020")
        position.longitude = Decimal("29.010")
        confirm_lock(db, db.query(TenantSettings).one(), load, "k")
        assert seen
        assert seen[0][1] is False
        assert seen[0][0] == (Decimal("41.020"), Decimal("29.010"))
        assert load.empty_km == Decimal("12.0")
