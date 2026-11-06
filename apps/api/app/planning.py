import math
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.chain import advice_lines, simulate
from app.geo import _haversine_km, cached_toll, locate, road_leg
from app.models import Load, TachoState, TenantSettings, Vehicle, VehiclePosition
from app.tacho import drive_minutes, fit, inserted_break, limits_from, reading_of, uses_extension

OPEN = ("atandi", "yolda")
DONE_OR_OPEN = ("atandi", "yolda", "teslim")
DEFAULTS = {"max_stops_return": 3, "chain_candidates": 5, "chain_max_wait_min": 360}


@dataclass
class Leg:
    km: Decimal
    seconds: int
    quality: str
    toll: Decimal | None
    toll_state: str | None


@dataclass
class Plan:
    value: Decimal
    refs: list[tuple[str, Decimal]] = field(default_factory=list)


def candidates(
    db: Session,
    settings: TenantSettings,
    load: Load,
    api_key: str | None,
    app_settings=None,
    pool: list[Load] | None = None,
    memo: dict | None = None,
) -> list[dict]:
    now = datetime.now(UTC)
    cfg = {name: getattr(app_settings, name, default) for name, default in DEFAULTS.items()}
    vehicles = db.query(Vehicle).filter(Vehicle.tenant_id == load.tenant_id).order_by(Vehicle.plate).all()
    base = _base_point(settings) if load.direction == "donus" else None
    base_cache: list[Leg | None] = []
    rows: list[dict] = []
    for vehicle in vehicles:
        position = _latest(db, vehicle.id)
        open_load = (
            db.query(Load)
            .filter(Load.vehicle_id == vehicle.id, Load.status.in_(OPEN), Load.id != load.id)
            .order_by(Load.deliver_end.desc())
            .first()
        )
        code = _reject(vehicle, position, settings, load, open_load, now)
        if code is None and load.direction == "donus" and _trip_count(db, vehicle, load) >= cfg["max_stops_return"]:
            code = "STOP_LIMIT"
        empty_km = loaded_km = rank = None
        quality = None
        drive_min = break_min = None
        extension = False
        toll = base_km = plan_value = None
        toll_unknown = False
        advice = chain_note = None
        if code is None and load.pickup_lat is not None and load.drop_lat is not None and position is not None:
            origin = _origin(position, open_load, load)
            from_gps = origin == (position.latitude, position.longitude)
            pickup = (load.pickup_lat, load.pickup_lng)
            drop = (load.drop_lat, load.drop_lng)
            empty = _leg(db, settings, origin, pickup, api_key, origin_coarse=from_gps, memo=memo)
            loaded = _leg(db, settings, pickup, drop, api_key, memo=memo)
            empty_km, loaded_km = empty.km, loaded.km
            quality = "google" if empty.quality == "google" and loaded.quality == "google" else "yaklasik"
            drive_min = drive_minutes(empty.seconds, loaded.seconds)
            limits = limits_from(settings)
            reading = reading_of(db.get(TachoState, vehicle.driver_id) if vehicle.driver_id else None)
            empty_min = math.ceil(empty.seconds / 60)
            loaded_min = math.ceil(loaded.seconds / 60)
            use_open = open_load is not None and bool(open_load.planned_drive_min) and reading is not None
            if use_open:
                previous = simulate(reading, [open_load.planned_drive_min], limits)
                code = previous.code
                begin, begin_ext, t0 = previous.end, previous.day_extended, _utc(open_load.deliver_end)
            else:
                code = fit(reading, drive_min, limits)
                begin, begin_ext, t0 = reading, None, now
            if code is None and reading is not None:
                first = simulate(begin, [empty_min], limits, begin_ext)
                pickup_clock = max(t0 + timedelta(minutes=first.elapsed_min), _utc(load.ready_at))
                second = simulate(first.end, [loaded_min], limits, first.day_extended)
                drop_clock = pickup_clock + timedelta(minutes=second.elapsed_min)
                if use_open:
                    code = first.code or second.code
                    if code is None and drop_clock > _utc(load.deliver_end):
                        code = "WINDOW"
            if code is None and reading is not None:
                whole = simulate(begin, [empty_min, loaded_min], limits, begin_ext)
                if use_open:
                    break_min = whole.break_min
                    extension = second.end.extensions_used > begin.extensions_used
                else:
                    break_min = inserted_break(reading.continuous_min, drive_min, limits.continuous_min)
                    extension = uses_extension(reading, drive_min, limits)
                leg = _base_leg(db, settings, load, base, api_key, base_cache, memo) if base is not None else None
                base_km = leg.km if leg is not None else None
                states = [item.toll_state for item in (empty, loaded, leg) if item is not None]
                toll_unknown = settings.toll_enabled and any(state in (None, "bilinmiyor") for state in states)
                toll = _toll_sum(settings, (empty, loaded, leg))
                rank = _rank(load, settings, empty_km, loaded_km, toll, base_km)
                plan = Plan(value=rank)
                if pool and settings.empty_km_cost is not None and load.freight_try is not None:
                    plan = _lookahead(
                        settings, load, vehicle, second.end, second.day_extended, drop_clock, base, pool, cfg, rank, limits, _trip_count(db, vehicle, load)
                    )
                plan_value = plan.value
                steps = whole
                if plan.refs:
                    chain_note = _chain_note(plan)
                elif leg is not None:
                    home = simulate(begin, [empty_min, loaded_min, math.ceil(leg.seconds / 60)], limits, begin_ext)
                    if home.code is None:
                        steps = home
                advice = " ".join(advice_lines(steps, limits))[:500] or None
        rows.append(
            {
                "vehicle_id": vehicle.id,
                "plate": vehicle.plate,
                "eligible": code is None,
                "code": code,
                "empty_km": empty_km,
                "loaded_km": loaded_km,
                "rank": rank,
                "distance_quality": quality,
                "drive_min": drive_min,
                "break_min": break_min,
                "uses_extension": extension,
                "toll_try": toll,
                "toll_unknown": toll_unknown,
                "base_km": base_km,
                "plan_value": plan_value if plan_value is not None else rank,
                "chain_note": chain_note,
                "advice": advice,
            }
        )
    rows.sort(key=lambda item: (item["eligible"], item["rank"] or Decimal("-1e18")), reverse=True)
    return rows


def assignment_for(db: Session, settings: TenantSettings, load: Load, vehicle: Vehicle, api_key: str | None) -> dict:
    row = next(item for item in candidates(db, settings, load, api_key) if item["vehicle_id"] == vehicle.id)
    if not row["eligible"]:
        raise ValueError(row["code"] or "VEHICLE_NOT_IN_SERVICE")
    return row


def confirm_lock(db: Session, settings: TenantSettings, load: Load, api_key: str | None) -> None:
    """Kilitlemede boş bacağı canlı konumla bir kez hassas ölçer. Cache 5 km hücredeyse sapmayı düzeltir."""
    if load.vehicle_id is None or load.pickup_lat is None:
        return
    position = _latest(db, load.vehicle_id)
    if position is None:
        return
    open_load = (
        db.query(Load)
        .filter(Load.vehicle_id == load.vehicle_id, Load.status.in_(OPEN), Load.id != load.id)
        .order_by(Load.deliver_end.desc())
        .first()
    )
    origin = _origin(position, open_load, load)
    if origin != (position.latitude, position.longitude):
        return
    empty = _leg(db, settings, origin, (load.pickup_lat, load.pickup_lng), api_key, origin_coarse=False)
    if empty.quality != "google":
        return
    load.empty_km = empty.km
    if load.loaded_km is not None:
        load.benefit_try = _rank(load, settings, empty.km, load.loaded_km, load.toll_try, load.base_km)
        load.rank_value = load.benefit_try


def _reject(vehicle: Vehicle, position: VehiclePosition | None, settings: TenantSettings, load: Load, open_load: Load | None, now: datetime) -> str | None:
    if vehicle.status != "serviste":
        return "VEHICLE_NOT_IN_SERVICE"
    recorded = _utc(position.recorded_at) if position is not None else None
    if recorded is None or now - recorded > timedelta(minutes=settings.gps_stale_minutes):
        return "STALE_POSITION"
    if vehicle.driver_id is None:
        return "NO_DRIVER"
    if load.tonnage > vehicle.capacity_tons:
        return "CAPACITY"
    if load.trailer_type != vehicle.trailer_type:
        return "TRAILER"
    if open_load is not None and _utc(open_load.deliver_end) > _utc(load.ready_at):
        return "OVERLAP"
    return None


def _origin(position: VehiclePosition, open_load: Load | None, load: Load) -> tuple[Decimal, Decimal]:
    if open_load is not None and open_load.drop_lat is not None and _utc(open_load.deliver_end) <= _utc(load.ready_at):
        return open_load.drop_lat, open_load.drop_lng
    return position.latitude, position.longitude


def _leg(db: Session, settings: TenantSettings, origin, destination, api_key: str | None, origin_coarse: bool = False, dest_coarse: bool = False, memo: dict | None = None) -> Leg:
    extra = {"origin_coarse": origin_coarse, "dest_coarse": dest_coarse, "memo": memo}
    if settings.toll_enabled:
        km, seconds, quality = road_leg(db, origin, destination, api_key, tolls=True, **extra)
        toll, state = cached_toll(db, origin, destination, **extra)
        return Leg(km, seconds, quality, toll, state)
    km, seconds, quality = road_leg(db, origin, destination, api_key, **extra)
    return Leg(km, seconds, quality, None, None)


def _toll_sum(settings: TenantSettings, legs) -> Decimal | None:
    if not settings.toll_enabled:
        return None
    total = Decimal("0")
    for leg in legs:
        if leg is None:
            continue
        if leg.toll is None:
            return None
        total += leg.toll
    return total


def _base_point(settings: TenantSettings) -> tuple[Decimal, Decimal] | None:
    if not settings.home_base_il:
        return None
    found = locate(settings.home_base_il, settings.home_base_ilce or "Merkez", None, None)
    if found is None:
        return None
    return found[0], found[1]


def _base_leg(db: Session, settings: TenantSettings, load: Load, base, api_key: str | None, cache: list, memo: dict | None = None) -> Leg | None:
    if cache:
        return cache[0]
    leg = None
    if load.drop_lat is not None:
        leg = _leg(db, settings, (load.drop_lat, load.drop_lng), base, api_key, memo=memo)
    cache.append(leg)
    return leg


def _rank(load: Load, settings: TenantSettings, empty_km: Decimal, loaded_km: Decimal, toll: Decimal | None, base_km: Decimal | None) -> Decimal:
    if load.freight_try is not None and settings.empty_km_cost is not None and settings.loaded_km_cost is not None:
        value = load.freight_try - empty_km * settings.empty_km_cost - loaded_km * settings.loaded_km_cost
        if base_km is not None:
            value -= base_km * settings.empty_km_cost
        if toll is not None:
            value -= toll
        return value
    return loaded_km - empty_km * Decimal("1.5")


def _trip_count(db: Session, vehicle: Vehicle, load: Load) -> int:
    last_out = (
        db.query(Load)
        .filter(Load.vehicle_id == vehicle.id, Load.direction == "gidis", Load.status.in_(DONE_OR_OPEN))
        .order_by(Load.deliver_end.desc())
        .first()
    )
    query = db.query(Load).filter(Load.vehicle_id == vehicle.id, Load.direction == "donus", Load.id != load.id)
    if last_out is not None:
        query = query.filter(Load.status.in_(DONE_OR_OPEN), Load.deliver_end > last_out.deliver_end)
    else:
        query = query.filter(Load.status.in_(OPEN))
    return query.count()


def _lookahead(settings, load, vehicle, reading, extended, clock, base, pool, cfg, rank: Decimal, limits, used: int) -> Plan:
    """Aynı tırın ilk yükten sonra alabileceği ardışık yükler. Yaklaşık mesafe kullanır, Routes çağrısı yapmaz.
    Aynı anda tek yük taşınır. Her adım boşaltma sonrası yeni yükleme olarak değerlendirilir."""
    plan = Plan(value=rank)
    slots = cfg["max_stops_return"] - used - 1
    if slots <= 0 or settings.empty_km_cost is None or settings.loaded_km_cost is None:
        return plan
    cost_e, cost_l = settings.empty_km_cost, settings.loaded_km_cost
    position = (load.drop_lat, load.drop_lng)
    taken = {str(load.id)}
    for _ in range(slots):
        options = []
        for other in pool:
            if str(other.id) in taken or other.pickup_lat is None or other.drop_lat is None or other.freight_try is None:
                continue
            if other.trailer_type != vehicle.trailer_type or other.tonnage > vehicle.capacity_tons:
                continue
            distance = _haversine_km(position[0], position[1], other.pickup_lat, other.pickup_lng)
            options.append((distance, other))
        options.sort(key=lambda item: item[0])
        best = None
        for distance, other in options[: cfg["chain_candidates"]]:
            loaded_km = _haversine_km(other.pickup_lat, other.pickup_lng, other.drop_lat, other.drop_lng)
            go = simulate(reading, [math.ceil(float(distance))], limits, extended)
            arrive = clock + timedelta(minutes=go.elapsed_min)
            ready = _utc(other.ready_at)
            if go.code is not None or ready - arrive > timedelta(minutes=cfg["chain_max_wait_min"]):
                continue
            pickup_clock = max(arrive, ready)
            carry = simulate(go.end, [math.ceil(float(loaded_km))], limits, go.day_extended)
            finish = pickup_clock + timedelta(minutes=carry.elapsed_min)
            if carry.code is not None or finish > _utc(other.deliver_end):
                continue
            gain = other.freight_try - distance * cost_e - loaded_km * cost_l
            if base is not None:
                gain -= (
                    _haversine_km(other.drop_lat, other.drop_lng, base[0], base[1])
                    - _haversine_km(position[0], position[1], base[0], base[1])
                ) * cost_e
            if gain > 0 and (best is None or gain > best[0]):
                best = (gain, other, carry, finish)
        if best is None:
            break
        gain, other, carry, finish = best
        taken.add(str(other.id))
        plan.value += gain
        plan.refs.append((other.reference, gain))
        position = (other.drop_lat, other.drop_lng)
        reading, extended, clock = carry.end, carry.day_extended, finish
    return plan


def _chain_note(plan: Plan) -> str:
    parts = [f"{ref} (yaklaşık +{_tl(value)} TL)" for ref, value in plan.refs]
    return ("Devam önerisi: " + ", ".join(parts))[:500]


def _tl(value: Decimal) -> str:
    return f"{float(value):,.0f}".replace(",", ".")


def _latest(db: Session, vehicle_id) -> VehiclePosition | None:
    return (
        db.query(VehiclePosition)
        .filter(VehiclePosition.vehicle_id == vehicle_id)
        .order_by(VehiclePosition.recorded_at.desc())
        .first()
    )


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
