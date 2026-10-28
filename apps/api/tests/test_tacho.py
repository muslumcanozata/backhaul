from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app
from app.models import TachoState
from app.tacho import Limits, Reading, assert_tighter, fit, inserted_break, uses_extension
from tests.helpers import auth, login
from tests.test_m2 import _csv, _firm, _line, _vehicle

LEGAL = Limits()


def _reading(**kwargs: int) -> Reading:
    base = dict(source="tahmini", continuous_min=0, daily_min=0, weekly_min=0, fortnight_min=0, extensions_used=0)
    base.update(kwargs)
    return Reading(**base)


def test_four_and_a_half_hours_inserts_a_forty_five_minute_break() -> None:
    assert inserted_break(270, 1) == 45
    assert inserted_break(0, 270) == 0
    assert inserted_break(200, 80) == 45
    assert inserted_break(270, 280) == 90


def test_daily_nine_hours_and_two_ten_hour_extensions() -> None:
    inside_nine = _reading(daily_min=480)
    assert fit(inside_nine, 60, LEGAL) is None
    assert uses_extension(inside_nine, 60, LEGAL) is False

    first_extension = _reading(daily_min=540)
    assert fit(first_extension, 60, LEGAL) is None
    assert uses_extension(first_extension, 60, LEGAL) is True

    second_extension = _reading(daily_min=540, extensions_used=1)
    assert fit(second_extension, 60, LEGAL) is None
    assert uses_extension(second_extension, 60, LEGAL) is True

    third = _reading(daily_min=540, extensions_used=2)
    assert fit(third, 60, LEGAL) == "TACHO_DAILY"
    assert fit(_reading(daily_min=540, extensions_used=0), 61, LEGAL) == "TACHO_DAILY"


def test_weekly_56_and_fortnight_90() -> None:
    assert fit(_reading(weekly_min=56 * 60), 1, LEGAL) == "TACHO_WEEKLY"
    assert fit(_reading(weekly_min=56 * 60 - 1), 1, LEGAL) is None
    assert fit(_reading(fortnight_min=90 * 60), 1, LEGAL) == "TACHO_FORTNIGHT"
    assert fit(_reading(fortnight_min=90 * 60 - 1), 1, LEGAL) is None


def test_company_limit_cannot_grow_the_legal_pack() -> None:
    assert_tighter(daily_min=540, warning_min=45)
    try:
        assert_tighter(daily_min=541)
    except ValueError:
        pass
    else:
        raise AssertionError("yasal paketin üstü kabul edildi")
    try:
        assert_tighter(warning_min=29)
    except ValueError:
        pass
    else:
        raise AssertionError("30 dakikanın altı kabul edildi")


def test_assignment_without_a_counter_is_refused(shared_client: TestClient) -> None:
    token = _firm(shared_client)
    vehicle_id = _vehicle(shared_client, token, "34 ABC 123", "25", "Ali Yılmaz", "5321112233", True)
    imported = shared_client.post("/loads/import", files=_csv(_line("G-1")), headers=auth(token))
    assert imported.status_code == 200, imported.text
    factory = app.state.runtime.factory
    with factory() as db:
        db.query(TachoState).delete()
        db.commit()
    load_id = shared_client.get("/loads", headers=auth(token)).json()[0]["id"]
    listed = shared_client.get(f"/loads/{load_id}/candidates", headers=auth(token))
    assert listed.json()[0]["code"] == "TACHO_UNKNOWN"
    refused = shared_client.post(f"/loads/{load_id}/assign", json={"vehicle_id": vehicle_id}, headers=auth(token))
    assert refused.status_code == 409
    assert refused.json()["detail"] == "TACHO_UNKNOWN"


def test_company_daily_limit_above_the_pack_is_rejected(shared_client: TestClient) -> None:
    token = _firm(shared_client)
    response = shared_client.patch("/settings", json={"tacho_daily_min": 541}, headers=auth(token))
    assert response.status_code == 422
    assert shared_client.get("/settings", headers=auth(token)).json()["tacho_daily_min"] == 540


def test_open_trip_that_no_longer_fits_raises_an_alert_and_stays_assigned(shared_client: TestClient) -> None:
    token = _firm(shared_client)
    vehicle_id = _vehicle(shared_client, token, "34 ABC 123", "25", "Ali Yılmaz", "5321112233", True)
    imported = shared_client.post("/loads/import", files=_csv(_line("G-1")), headers=auth(token))
    assert imported.status_code == 200, imported.text
    load_id = shared_client.get("/loads", headers=auth(token)).json()[0]["id"]
    assigned = shared_client.post(f"/loads/{load_id}/assign", json={"vehicle_id": vehicle_id}, headers=auth(token))
    assert assigned.status_code == 200, assigned.text
    factory = app.state.runtime.factory
    with factory() as db:
        state = db.query(TachoState).one()
        state.daily_min = 600
        state.extensions_used = 2
        db.commit()
    later = datetime.now(UTC) + timedelta(minutes=5)
    position = shared_client.post(
        f"/vehicles/{vehicle_id}/position",
        json={"latitude": "41.02", "longitude": "28.98", "speed_kmh": "0", "recorded_at": later.isoformat()},
        headers=auth(token),
    )
    assert position.status_code == 200, position.text
    alerts = shared_client.get("/alerts", headers=auth(token)).json()
    assert "PLAN_INFEASIBLE" in {item["code"] for item in alerts}
    assert shared_client.get("/loads", headers=auth(token)).json()[0]["status"] == "atandi"
