import json
import math
import urllib.parse
import urllib.request
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import RoadCache
from app.places import Place, find_place


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


def _cell(value: Decimal) -> str:
    return f"{float(value):.3f}"


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
) -> tuple[Decimal, int, str]:
    cache_key = "|".join(_cell(value) for value in (*origin, *destination))
    cached = db.get(RoadCache, cache_key)
    if cached is not None:
        return cached.kilometers, cached.seconds, cached.quality
    kilometers, seconds, quality = _measure(origin, destination, api_key, opener)
    db.add(RoadCache(cache_key=cache_key, kilometers=kilometers, seconds=seconds, quality=quality))
    db.flush()
    return kilometers, seconds, quality


def _measure(
    origin: tuple[Decimal, Decimal],
    destination: tuple[Decimal, Decimal],
    api_key: str | None,
    opener,
) -> tuple[Decimal, int, str]:
    approximate = _haversine_km(*origin, *destination)
    seconds = max(1, int(float(approximate) / 60 * 3600))
    if not api_key:
        return approximate, seconds, "yaklasik"
    body = {
        "origins": [_waypoint(origin)],
        "destinations": [_waypoint(destination)],
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_UNAWARE",
    }
    request = urllib.request.Request(
        "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix",
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "distanceMeters,duration,condition",
        },
        method="POST",
    )
    try:
        with opener(request, timeout=20) as response:
            payload = json.loads(response.read().decode())
    except Exception:
        return approximate, seconds, "yaklasik"
    row = payload[0] if isinstance(payload, list) and payload else payload
    if not isinstance(row, dict) or row.get("condition") not in {None, "ROUTE_EXISTS"}:
        return approximate, seconds, "yaklasik"
    meters = row.get("distanceMeters")
    if meters is None:
        return approximate, seconds, "yaklasik"
    kilometers = Decimal(str(round(float(meters) / 1000, 1)))
    duration = str(row.get("duration") or "0s").rstrip("s")
    try:
        google_seconds = int(float(duration))
    except ValueError:
        google_seconds = seconds
    return kilometers, google_seconds, "google"


def _waypoint(point: tuple[Decimal, Decimal]) -> dict:
    return {"waypoint": {"location": {"latLng": {"latitude": float(point[0]), "longitude": float(point[1])}}}}
