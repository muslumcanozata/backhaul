from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

from app.netgsm import render


def _load(**extra):
    base = dict(
        reference="G-1042",
        direction="gidis",
        pickup_il="Ordu",
        pickup_ilce="Altinordu",
        drop_il="Istanbul",
        drop_ilce="Tuzla",
        drop_lat=Decimal("40.816000"),
        drop_lng=Decimal("29.300000"),
        ready_at=datetime(2026, 11, 1, 5, 0, tzinfo=UTC),
        deliver_start=datetime(2026, 11, 1, 15, 0, tzinfo=UTC),
        deliver_end=datetime(2026, 11, 1, 19, 0, tzinfo=UTC),
    )
    base.update(extra)
    return SimpleNamespace(**base)


def test_assignment_sms_includes_maps_pin() -> None:
    text = render("Camsan", _load(), "34ABC123", "atama")
    assert "ATAMA GIDIS" in text
    assert "Harita https://maps.google.com/?q=40.816000,29.300000" in text
    assert "Bosaltma Istanbul/Tuzla" in text


def test_maps_falls_back_to_place_search() -> None:
    text = render("Camsan", _load(drop_lat=None, drop_lng=None), "34ABC123", "guncelleme")
    assert "GUNCELLEME" in text
    assert "Harita https://maps.google.com/?q=Istanbul%20Tuzla" in text


def test_cancel_sms_has_no_maps_link() -> None:
    text = render("Camsan", _load(), "34ABC123", "iptal")
    assert "IPTAL" in text
    assert "Harita" not in text
