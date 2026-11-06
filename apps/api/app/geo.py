import json
import math
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import RoadCache, RoutesUsage
from app.places import Place, find_place

FINE = 0.001
COARSE = 0.05
APPROVE_BATCH = 333
GOOGLE_TTL = timedelta(days=90)
TOLL_TTL = timedelta(days=30)
BACKOFF = (
    timedelta(0),
    timedelta(minutes=15),
    timedelta(hours=1),
    timedelta(hours=6),
    timedelta(days=1),
)


def locate(
    il: str,
    ilce: str,
    address: str | None,
    api_key: str | None,
    opener=urllib.request.urlopen,
) -> tuple[Decimal, Decimal, str] | None:
    place = find_place(il, ilce)
    if place is None:
        return None
    if api_key:
        point = _google_point(place, address, api_key, opener)
        if point is not None:
            return point[0], point[1], "google"
    return place.latitude, place.longitude, "yaklasik"


def _google_point(place: Place, address: str | None, api_key: str, opener) -> tuple[Decimal, Decimal] | None:
    query = ", ".join(part for part in (address, place.ilce, place.il, "Türkiye") if part)
    params = urllib.parse.urlencode({"address": query, "region": "tr", "language": "tr", "key": api_key})
    request = urllib.request.Request(f"https://maps.googleapis.com/maps/api/geocode/json?{params}")
    try:
        with opener(request, timeout=20) as response:
            payload = json.loads(response.read().decode())
    except Exception:
        return None
    if payload.get("status") != "OK" or not payload.get("results"):
        return None
    location = payload["results"][0]["geometry"]["location"]
    return Decimal(str(location["lat"])), Decimal(str(location["lng"]))


def _cell(value: Decimal, step: float = FINE) -> str:
    snapped = round(round(float(value) / step) * step, 6)
    decimals = 3 if step < 0.01 else 2
    return f"{snapped:.{decimals}f}"


def _snap(value: Decimal, step: float) -> Decimal:
    return Decimal(_cell(value, step))


def cache_key(
    origin: tuple[Decimal, Decimal],
    destination: tuple[Decimal, Decimal],
    origin_coarse: bool = False,
    dest_coarse: bool = False,
) -> str:
    ostep = COARSE if origin_coarse else FINE
    dstep = COARSE if dest_coarse else FINE
    return "|".join(
        (
            _cell(origin[0], ostep),
            _cell(origin[1], ostep),
            _cell(destination[0], dstep),
            _cell(destination[1], dstep),
        )
    )


def _haversine_km(lat1: Decimal, lng1: Decimal, lat2: Decimal, lng2: Decimal) -> Decimal:
    radius = 6371.0
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    d_phi = math.radians(float(lat2) - float(lat1))
    d_lng = math.radians(float(lng2) - float(lng1))
    arc = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lng / 2) ** 2
    kilometers = 2 * radius * math.asin(math.sqrt(arc))
    return Decimal(str(round(kilometers * 1.3, 1)))


def road_leg(
    db: Session,
    origin: tuple[Decimal, Decimal],
    destination: tuple[Decimal, Decimal],
    api_key: str | None,
    opener=urllib.request.urlopen,
    tolls: bool = False,
    origin_coarse: bool = False,
    dest_coarse: bool = False,
    limit: int | None = None,
    now: datetime | None = None,
    memo: dict | None = None,
) -> tuple[Decimal, int, str]:
    key = cache_key(origin, destination, origin_coarse, dest_coarse)
    if memo is not None and key in memo:
        return memo[key]
    cached = db.get(RoadCache, key)
    clock = now or datetime.now(UTC)
    quota = _limit(limit)
    if cached is not None and _usable(cached, tolls, clock):
        _hit(db)
        result = cached.kilometers, cached.seconds, cached.quality
        if memo is not None:
            memo[key] = result
        return result
    if not api_key:
        result = _store_approx(db, cached, key, origin, destination, clock)
        if memo is not None:
            memo[key] = result
        return result
    if not _consume(db, quota):
        approximate = _haversine_km(*origin, *destination)
        result = approximate, max(1, int(float(approximate) / 60 * 3600)), "yaklasik"
        if memo is not None:
            memo[key] = result
        return result
    measured_from = _point(origin, origin_coarse), _point(destination, dest_coarse)
    measured = _measure(*measured_from, api_key, opener, tolls)
    if cached is None:
        cached = RoadCache(cache_key=key, kilometers=measured[0], seconds=measured[1], quality=measured[2], tries=0)
        db.add(cached)
    if measured[2] == "google":
        cached.kilometers, cached.seconds, cached.quality = measured[0], measured[1], measured[2]
        cached.tries = 0
        cached.fetched_at = clock.replace(tzinfo=None)
        if tolls:
            cached.toll_try, cached.toll_state = measured[3], measured[4]
    elif cached.quality != "google":
        cached.kilometers, cached.seconds, cached.quality = measured[0], measured[1], measured[2]
        cached.tries = (cached.tries or 0) + 1
        cached.fetched_at = clock.replace(tzinfo=None)
    else:
        cached.tries = (cached.tries or 0) + 1
        cached.fetched_at = clock.replace(tzinfo=None)
    db.flush()
    result = cached.kilometers, cached.seconds, cached.quality
    if memo is not None:
        memo[key] = result
    return result


def cached_toll(
    db: Session,
    origin: tuple[Decimal, Decimal],
    destination: tuple[Decimal, Decimal],
    origin_coarse: bool = False,
    dest_coarse: bool = False,
) -> tuple[Decimal | None, str | None]:
    """Önbellekteki geçiş ücreti. Durum: yok, bilinen, bilinmiyor. Hesaplanmadıysa None."""
    cached = db.get(RoadCache, cache_key(origin, destination, origin_coarse, dest_coarse))
    if cached is None or cached.quality != "google":
        return None, None
    return cached.toll_try, cached.toll_state


def usage_snapshot(db: Session, limit: int | None = None) -> dict:
    quota = _limit(limit)
    row = _today(db)
    allowed = quota + row.approved_extra
    return {
        "routes_today": row.calls,
        "routes_limit": quota,
        "routes_allowed": allowed,
        "routes_cache_hits": row.cache_hits,
        "routes_blocked": row.blocked,
        "routes_needs_approval": quota > 0 and row.calls >= allowed,
    }


def approve_extra(db: Session, extra: int = APPROVE_BATCH) -> dict:
    row = _today(db)
    row.approved_extra += extra
    row.blocked = 0
    db.flush()
    return usage_snapshot(db)


def _today(db: Session) -> RoutesUsage:
    day = datetime.now(ZoneInfo("Europe/Istanbul")).date().isoformat()
    row = db.get(RoutesUsage, day)
    if row is None:
        row = RoutesUsage(day=day, calls=0, cache_hits=0, approved_extra=0, blocked=0)
        db.add(row)
        db.flush()
    return row


def _limit(limit: int | None) -> int:
    return get_settings().routes_daily_limit if limit is None else limit


def _hit(db: Session) -> None:
    _today(db).cache_hits += 1


def _consume(db: Session, limit: int) -> bool:
    if limit <= 0:
        return True
    row = _today(db)
    if row.calls >= limit + row.approved_extra:
        row.blocked += 1
        return False
    row.calls += 1
    return True


def _usable(cached: RoadCache, tolls: bool, now: datetime) -> bool:
    fetched = _as_utc(cached.fetched_at)
    if cached.quality == "google":
        if fetched is not None and now - fetched > GOOGLE_TTL:
            return False
        if tolls:
            if cached.toll_state is None:
                return False
            if fetched is not None and now - fetched > TOLL_TTL:
                return False
        return True
    if fetched is None:
        return False
    wait = BACKOFF[min(cached.tries or 0, len(BACKOFF) - 1)]
    return now - fetched < wait


def _store_approx(
    db: Session,
    cached: RoadCache | None,
    key: str,
    origin: tuple[Decimal, Decimal],
    destination: tuple[Decimal, Decimal],
    clock: datetime,
) -> tuple[Decimal, int, str]:
    approximate = _haversine_km(*origin, *destination)
    seconds = max(1, int(float(approximate) / 60 * 3600))
    if cached is None:
        cached = RoadCache(cache_key=key, kilometers=approximate, seconds=seconds, quality="yaklasik", tries=1)
        db.add(cached)
    else:
        cached.kilometers, cached.seconds, cached.quality = approximate, seconds, "yaklasik"
        cached.tries = max(cached.tries or 0, 1)
    cached.fetched_at = clock.replace(tzinfo=None)
    db.flush()
    return cached.kilometers, cached.seconds, cached.quality


def _point(pair: tuple[Decimal, Decimal], coarse: bool) -> tuple[Decimal, Decimal]:
    if not coarse:
        return pair
    return _snap(pair[0], COARSE), _snap(pair[1], COARSE)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def _measure(
    origin: tuple[Decimal, Decimal],
    destination: tuple[Decimal, Decimal],
    api_key: str | None,
    opener,
    tolls: bool = False,
) -> tuple[Decimal, int, str, Decimal | None, str | None]:
    approximate = _haversine_km(*origin, *destination)
    seconds = max(1, int(float(approximate) / 60 * 3600))
    fallback = (approximate, seconds, "yaklasik", None, None)
    if not api_key:
        return fallback
    origin_point = _waypoint(origin)
    if tolls:
        origin_point["routeModifiers"] = {"vehicleInfo": {"emissionType": "DIESEL"}}
    body = {
        "origins": [origin_point],
        "destinations": [_waypoint(destination)],
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_UNAWARE",
    }
    mask = "distanceMeters,duration,condition"
    if tolls:
        body["extraComputations"] = ["TOLLS"]
        mask += ",travelAdvisory.tollInfo"
    request = urllib.request.Request(
        "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix",
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": mask,
        },
        method="POST",
    )
    try:
        with opener(request, timeout=20) as response:
            payload = json.loads(response.read().decode())
    except Exception:
        return fallback
    row = payload[0] if isinstance(payload, list) and payload else payload
    if not isinstance(row, dict) or row.get("condition") not in {None, "ROUTE_EXISTS"}:
        return fallback
    meters = row.get("distanceMeters")
    if meters is None:
        return fallback
    kilometers = Decimal(str(round(float(meters) / 1000, 1)))
    duration = str(row.get("duration") or "0s").rstrip("s")
    try:
        google_seconds = int(float(duration))
    except ValueError:
        google_seconds = seconds
    toll_try, toll_state = parse_toll(row) if tolls else (None, None)
    return kilometers, google_seconds, "google", toll_try, toll_state


def parse_toll(row: dict) -> tuple[Decimal | None, str]:
    """Routes yanıtından geçiş ücreti. tollInfo yoksa güzergâhta ücret yok.
    tollInfo var ama fiyat yoksa ücret bilinmiyor. TRY dışı para birimi bilinmiyor sayılır."""
    info = (row.get("travelAdvisory") or {}).get("tollInfo")
    if info is None:
        return Decimal("0"), "yok"
    prices = info.get("estimatedPrice") or []
    if not prices:
        return None, "bilinmiyor"
    total = Decimal("0")
    for money in prices:
        if money.get("currencyCode") != "TRY":
            return None, "bilinmiyor"
        total += Decimal(str(money.get("units") or 0)) + Decimal(str(money.get("nanos") or 0)) / Decimal(1_000_000_000)
    return total.quantize(Decimal("0.01")), "bilinen"


def _waypoint(point: tuple[Decimal, Decimal]) -> dict:
    return {"waypoint": {"location": {"latLng": {"latitude": float(point[0]), "longitude": float(point[1])}}}}
