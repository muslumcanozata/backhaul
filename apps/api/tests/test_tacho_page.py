from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.main import app
from app.models import TenantSettings
from app.seyir import TachoPacket, apply_tacho
from tests.helpers import auth
from tests.test_m2 import _firm


def test_tacho_page_shows_limits_and_history(shared_client: TestClient) -> None:
    token = _firm(shared_client)
    created = shared_client.post(
        "/drivers",
        json={"name": "Ali Yılmaz", "phone": "5321112233", "card_id": "CARD1"},
        headers=auth(token),
    )
    assert created.status_code == 200, created.text
    driver_id = created.json()["id"]
    first = datetime(2026, 11, 1, 8, 0, tzinfo=UTC)
    second = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
    with app.state.runtime.factory() as db:
        settings = db.query(TenantSettings).one()
        apply_tacho(
            db,
            settings.tenant_id,
            [
                TachoPacket("Ali Yılmaz", "CARD1", None, first, 400, 3000, 800, None, 200, 2),
                TachoPacket("Ali Yılmaz", "CARD1", None, second, 120, 2000, 1500, None, 90, 1),
            ],
            settings,
        )
        db.commit()
    rows = shared_client.get("/tacho", headers=auth(token))
    assert rows.status_code == 200, rows.text
    row = rows.json()[0]
    assert row["driver_id"] == driver_id
    assert row["daily_used"] == 420
    assert row["daily_limit"] == 540
    assert row["daily_remain"] == 120
    assert row["weekly_used"] == 1360
    assert row["weekly_limit"] == 3360
    assert row["fortnight_used"] == 1500
    assert row["fortnight_limit"] == 5400
    assert row["continuous_used"] == 180
    assert row["continuous_limit"] == 270
    assert row["extensions_used"] == 1
    assert row["source"] == "olculmus"
    detail = shared_client.get(f"/tacho/{driver_id}", headers=auth(token))
    assert detail.status_code == 200, detail.text
    samples = detail.json()["samples"]
    assert len(samples) == 2
    assert samples[0]["daily_min"] == 420
    assert samples[1]["daily_min"] == 140
