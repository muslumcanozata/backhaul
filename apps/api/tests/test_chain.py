import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient

from app.chain import advice_lines, format_minutes, simulate
from app.geo import _measure, parse_toll, road_leg
from app.main import app
from app.models import Load, RoadCache, TachoState
from app.tacho import Limits, Reading
from tests.helpers import auth
from tests.test_m2 import _csv, _line, _vehicle
from tests.test_m4 import _firm, _place

LIMITS = Limits()


def _reading(**kwargs) -> Reading:
    base = dict(source="olculmus", continuous_min=0, daily_min=0, weekly_min=0, fortnight_min=0, extensions_used=0, split_break_min=0)
    base.update(kwargs)
    return Reading(**base)


def test_simulation_adds_a_break_after_four_and_a_half_hours() -> None:
    sim = simulate(_reading(), [300], LIMITS)
    assert sim.code is None
    assert sim.drive_min == 300
    assert sim.break_min == 45
    assert sim.elapsed_min == 345
    assert [(step.kind, step.after_drive_min) for step in sim.steps if step.kind != "drive"] == [("break", 270)]


def test_simulation_adds_daily_rest_when_the_day_is_full() -> None:
    sim = simulate(_reading(daily_min=500), [200], LIMITS)
    assert sim.code is None
    assert sim.rest_count == 1
    assert sim.end.daily_min == 100


def test_simulation_uses_an_extension_once_per_day() -> None:
    sim = simulate(_reading(daily_min=500), [80], LIMITS)
    assert sim.code is None
    assert sim.rest_count == 0
    assert sim.end.extensions_used == 1


def test_simulation_stops_at_the_weekly_limit() -> None:
    sim = simulate(_reading(weekly_min=LIMITS.weekly_min - 10), [60], LIMITS)
    assert sim.code == "TACHO_WEEKLY"


def test_advice_is_time_only_and_has_no_place() -> None:
    sim = simulate(_reading(), [300], LIMITS)
    lines = advice_lines(sim, LIMITS)
    assert lines[0] == "4 saat 30 dk sürüşten sonra 45 dk mola ver."
    assert lines[-1].startswith("Bu sürüşün sonunda günlük sürüşe")
    assert format_minutes(130) == "2 saat 10 dk"


def test_toll_parsing_separates_none_unknown_and_priced() -> None:
    assert parse_toll({}) == (Decimal("0"), "yok")
    assert parse_toll({"travelAdvisory": {"tollInfo": {}}}) == (None, "bilinmiyor")
    priced = {"travelAdvisory": {"tollInfo": {"estimatedPrice": [{"currencyCode": "TRY", "units": "120", "nanos": 500000000}]}}}
    assert parse_toll(priced) == (Decimal("120.50"), "bilinen")
    foreign = {"travelAdvisory": {"tollInfo": {"estimatedPrice": [{"currencyCode": "USD", "units": "4"}]}}}
    assert parse_toll(foreign) == (None, "bilinmiyor")


class _Reply:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


def test_toll_is_requested_only_when_enabled_and_cached_after() -> None:
    sent = []

    def opener(request, timeout):
        sent.append((json.loads(request.data.decode()), request.headers))
        return _Reply([{"condition": "ROUTE_EXISTS", "distanceMeters": 100000, "duration": "3600s", "travelAdvisory": {"tollInfo": {"estimatedPrice": [{"currencyCode": "TRY", "units": "75"}]}}}])

    origin, destination = (Decimal("41.0"), Decimal("29.0")), (Decimal("40.0"), Decimal("30.0"))
    plain = _measure(origin, destination, "test-key", opener)
    body, headers = sent[0]
    assert "extraComputations" not in body
    assert "tollInfo" not in headers["X-goog-fieldmask"]
    assert plain[3] is None

    priced = _measure(origin, destination, "test-key", opener, tolls=True)
    body, headers = sent[1]
    assert body["extraComputations"] == ["TOLLS"]
    assert "travelAdvisory.tollInfo" in headers["X-goog-fieldmask"]
    assert priced[3:] == (Decimal("75.00"), "bilinen")


def test_road_leg_without_a_key_never_calls_the_network(shared_client: TestClient) -> None:
    def forbidden(request, timeout):
        raise AssertionError("Ağ çağrısı yapılmamalı")

    factory = app.state.runtime.factory
    with factory() as db:
        km, seconds, quality = road_leg(db, (Decimal("41.0"), Decimal("29.0")), (Decimal("40.0"), Decimal("30.0")), None, forbidden, tolls=True)
        assert quality == "yaklasik"
        row = db.query(RoadCache).one()
        assert row.toll_state is None


def _leg_ten(db, origin, destination, api_key, tolls=False):
    return Decimal("10.0"), 600, "google"


def _setup_pool(client: TestClient, token: str):
    vehicle = _vehicle(client, token, "34 AAA 1", "25", "Ali Yılmaz", "5321112233", True)
    client.post(
        f"/vehicles/{vehicle}/position",
        json={"latitude": "41.000", "longitude": "29.000", "recorded_at": datetime.now(UTC).isoformat()},
        headers=auth(token),
    )
    imported = client.post(
        "/loads/import",
        files=_csv(_line("A", direction="donus", freight="5000"), _line("B", direction="donus", freight="5000")),
        headers=auth(token),
    )
    assert imported.status_code == 200, imported.text
    _place("A", "41.100")
    _place("B", "41.105")
    now = datetime.now(UTC)
    factory = app.state.runtime.factory
    with factory() as db:
        first = db.query(Load).filter(Load.reference == "A").one()
        second = db.query(Load).filter(Load.reference == "B").one()
        first.ready_at, first.deliver_start, first.deliver_end = now, now, now + timedelta(hours=1)
        second.ready_at, second.deliver_start, second.deliver_end = now + timedelta(hours=2), now + timedelta(hours=2), now + timedelta(days=2)
        db.commit()
    return vehicle


def _loads(client: TestClient, token: str) -> dict:
    return {item["reference"]: item for item in client.get("/loads", headers=auth(token)).json()}


def test_one_load_is_assigned_now_and_the_next_is_only_suggested(shared_client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.planning.road_leg", _leg_ten)
    token = _firm(shared_client, "a-tasima", "a@example.com")
    vehicle = _setup_pool(shared_client, token)
    patched = shared_client.patch(
        "/settings",
        json={"empty_km_cost": "10", "loaded_km_cost": "10", "auto_assign_estimated": True},
        headers=auth(token),
    )
    assert patched.status_code == 200, patched.text
    loads = _loads(shared_client, token)
    assigned = [item for item in loads.values() if item["vehicle_id"] == vehicle]
    assert len(assigned) == 1
    first = assigned[0]
    other = "B" if first["reference"] == "A" else "A"
    assert first["chain_note"].startswith("Devam önerisi")
    assert other in first["chain_note"]
    assert Decimal(first["chain_value_try"]) > Decimal(first["benefit_try"])
    assert loads[other]["vehicle_id"] is None
    assert first["driver_advice"]


def test_next_load_is_assigned_after_the_first_is_locked(shared_client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.planning.road_leg", _leg_ten)
    token = _firm(shared_client, "a-tasima", "a@example.com")
    vehicle = _setup_pool(shared_client, token)
    shared_client.patch(
        "/settings",
        json={"empty_km_cost": "10", "loaded_km_cost": "10", "auto_assign_estimated": True},
        headers=auth(token),
    )
    loads = _loads(shared_client, token)
    first = next(item for item in loads.values() if item["vehicle_id"] == vehicle)
    factory = app.state.runtime.factory
    with factory() as db:
        row = db.query(Load).filter(Load.reference == first["reference"]).one()
        row.locked = True
        row.deliver_end = datetime.now(UTC) + timedelta(hours=1)
        second = db.query(Load).filter(Load.reference != first["reference"]).one()
        second.ready_at = datetime.now(UTC) + timedelta(hours=2)
        db.commit()
    shared_client.patch("/settings", json={"empty_km_cost": "11"}, headers=auth(token))
    after = _loads(shared_client, token)
    assert after[first["reference"]]["locked"] is True
    assert after[first["reference"]]["vehicle_id"] == vehicle
    other = "B" if first["reference"] == "A" else "A"
    assert after[other]["vehicle_id"] == vehicle
    assert after[other]["status"] == "atandi"


def test_a_fourth_return_load_is_blocked_by_the_stop_limit(shared_client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.planning.road_leg", _leg_ten)
    token = _firm(shared_client, "a-tasima", "a@example.com")
    vehicle = _setup_pool(shared_client, token)
    factory = app.state.runtime.factory
    now = datetime.now(UTC)
    with factory() as db:
        template = db.query(Load).filter(Load.reference == "A").one()
        for index in range(3):
            db.add(
                Load(
                    tenant_id=template.tenant_id,
                    vehicle_id=UUID(vehicle),
                    reference=f"X{index}",
                    direction="donus",
                    pickup_il="İstanbul",
                    pickup_ilce="Pendik",
                    drop_il="Ankara",
                    drop_ilce="Çankaya",
                    pickup_lat=Decimal("41.0"),
                    pickup_lng=Decimal("29.0"),
                    drop_lat=Decimal("41.0"),
                    drop_lng=Decimal("29.0"),
                    tonnage=Decimal("10"),
                    trailer_type="tenteli",
                    ready_at=now,
                    deliver_start=now,
                    deliver_end=now,
                    status="atandi",
                    locked=True,
                )
            )
        db.commit()
        target = db.query(Load).filter(Load.reference == "B").one()
        target_id = str(target.id)
    rows = shared_client.get(f"/loads/{target_id}/candidates", headers=auth(token)).json()
    row = next(item for item in rows if item["vehicle_id"] == vehicle)
    assert row["code"] == "STOP_LIMIT"


def test_home_base_return_leg_lowers_the_benefit(shared_client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.planning.road_leg", _leg_ten)
    token = _firm(shared_client, "a-tasima", "a@example.com")
    vehicle = _setup_pool(shared_client, token)
    shared_client.patch(
        "/settings",
        json={"empty_km_cost": "10", "loaded_km_cost": "10", "auto_assign_estimated": True},
        headers=auth(token),
    )
    before = next(item for item in _loads(shared_client, token).values() if item["vehicle_id"] == vehicle)
    bad = shared_client.patch("/settings", json={"home_base_il": "Yok", "home_base_ilce": "Yok"}, headers=auth(token))
    assert bad.status_code == 422
    ok = shared_client.patch("/settings", json={"home_base_il": "Ankara", "home_base_ilce": "Çankaya"}, headers=auth(token))
    assert ok.status_code == 200, ok.text
    assert ok.json()["home_base_il"] == "Ankara"
    after = next(item for item in _loads(shared_client, token).values() if item["vehicle_id"] == vehicle)
    assert Decimal(before["benefit_try"]) - Decimal(after["benefit_try"]) == Decimal("100.00")
    assert after["base_km"] == "10.0"


def _leg_with_tolls(db, origin, destination, api_key, tolls=False):
    assert tolls is True
    return Decimal("10.0"), 600, "google"


def test_unknown_toll_keeps_the_pair_out_and_known_toll_is_charged(shared_client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.planning.road_leg", _leg_with_tolls)
    monkeypatch.setattr("app.planning.cached_toll", lambda db, origin, destination: (None, "bilinmiyor"))
    token = _firm(shared_client, "a-tasima", "a@example.com")
    vehicle = _setup_pool(shared_client, token)
    shared_client.patch(
        "/settings",
        json={"empty_km_cost": "10", "loaded_km_cost": "10", "auto_assign_estimated": True, "toll_enabled": True},
        headers=auth(token),
    )
    assert not [item for item in _loads(shared_client, token).values() if item["vehicle_id"] == vehicle]

    monkeypatch.setattr("app.planning.cached_toll", lambda db, origin, destination: (Decimal("120"), "bilinen"))
    shared_client.patch("/settings", json={"empty_km_cost": "10.5"}, headers=auth(token))
    assigned = [item for item in _loads(shared_client, token).values() if item["vehicle_id"] == vehicle]
    assert len(assigned) == 1
    assert Decimal(assigned[0]["toll_try"]) == Decimal("240.00")
