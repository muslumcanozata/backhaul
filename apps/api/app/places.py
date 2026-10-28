import json
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

_FOLD = str.maketrans(
    {
        "İ": "i",
        "I": "i",
        "ı": "i",
        "Ş": "s",
        "ş": "s",
        "Ğ": "g",
        "ğ": "g",
        "Ü": "u",
        "ü": "u",
        "Ö": "o",
        "ö": "o",
        "Ç": "c",
        "ç": "c",
    }
)


def fold(value: str) -> str:
    return " ".join(value.strip().translate(_FOLD).lower().split())


@dataclass(frozen=True)
class Place:
    il: str
    ilce: str
    latitude: Decimal
    longitude: Decimal


@lru_cache
def _index() -> dict[tuple[str, str], Place]:
    raw = json.loads((Path(__file__).parent / "data" / "yerler.json").read_text(encoding="utf-8"))
    index: dict[tuple[str, str], Place] = {}
    for il, body in raw.items():
        point = Place(il=il, ilce="", latitude=Decimal(str(body["lat"])), longitude=Decimal(str(body["lng"])))
        for ilce in body["ilce"]:
            index[(fold(il), fold(ilce))] = Place(
                il=il,
                ilce=ilce,
                latitude=point.latitude,
                longitude=point.longitude,
            )
    return index


def find_place(il: str, ilce: str) -> Place | None:
    return _index().get((fold(il), fold(ilce)))
