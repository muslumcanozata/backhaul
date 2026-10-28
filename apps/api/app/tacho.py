import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models import Alert, Load, TachoState, TenantSettings, Vehicle, VehiclePosition

ISTANBUL = ZoneInfo("Europe/Istanbul")
PACK = "TR-AETR-2026"

LEGAL_CONTINUOUS = 270
LEGAL_DAILY = 540
LEGAL_EXTENDED = 600
LEGAL_EXTENSIONS = 2
LEGAL_WEEKLY = 56 * 60
LEGAL_FORTNIGHT = 90 * 60
LEGAL_BREAK = 45
LEGAL_SPLIT_FIRST = 15
LEGAL_SPLIT_SECOND = 30
LEGAL_WARNING = 30
DRIVING_SPEED = Decimal("5")
SAMPLE_GAP_MIN = 20


@dataclass(frozen=True)
class Limits:
    continuous_min: int = LEGAL_CONTINUOUS
    daily_min: int = LEGAL_DAILY
    extended_min: int = LEGAL_EXTENDED
    extensions: int = LEGAL_EXTENSIONS
    weekly_min: int = LEGAL_WEEKLY
    fortnight_min: int = LEGAL_FORTNIGHT
    warning_min: int = LEGAL_WARNING


@dataclass(frozen=True)
class Reading:
    source: str
    continuous_min: int
    daily_min: int
    weekly_min: int
    fortnight_min: int
    extensions_used: int
    split_break_min: int = 0


def limits_from(settings: TenantSettings) -> Limits:
    return Limits(
        continuous_min=settings.tacho_continuous_min,
        daily_min=settings.tacho_daily_min,
        extended_min=settings.tacho_extended_min,
        extensions=settings.tacho_extensions,
        weekly_min=settings.tacho_weekly_min,
        fortnight_min=settings.tacho_fortnight_min,
        warning_min=settings.tacho_warning_min,
    )


def assert_tighter(
    continuous_min: int | None = None,
    daily_min: int | None = None,
    extended_min: int | None = None,
    extensions: int | None = None,
    weekly_min: int | None = None,
    fortnight_min: int | None = None,
    warning_min: int | None = None,
) -> None:
    pairs = (
        (continuous_min, LEGAL_CONTINUOUS),
        (daily_min, LEGAL_DAILY),
        (extended_min, LEGAL_EXTENDED),
        (extensions, LEGAL_EXTENSIONS),
        (weekly_min, LEGAL_WEEKLY),
        (fortnight_min, LEGAL_FORTNIGHT),
    )
    for value, legal in pairs:
        if value is not None and (value < 1 or value > legal):
            raise ValueError("Şirket limiti yasal paketi büyütmez")
    if warning_min is not None and warning_min < LEGAL_WARNING:
        raise ValueError("Ön uyarı payı 30 dakikanın altına inmez")
    if daily_min is not None and extended_min is not None and extended_min < daily_min:
        raise ValueError("Uzatılmış günlük sürüş, günlük sınırın altında kalamaz")


def inserted_break(continuous_min: int, needed_min: int, continuous_limit: int = LEGAL_CONTINUOUS) -> int:
    breaks = 0
    cursor = continuous_min
    left = needed_min
    while left > 0:
        room = max(continuous_limit - cursor, 0)
        if left <= room:
            return breaks
        left -= room
        breaks += LEGAL_BREAK
        cursor = 0
    return breaks


def fit(reading: Reading | None, needed_min: int, limits: Limits) -> str | None:
    if reading is None or reading.source not in {"tahmini", "olculmus"}:
        return "TACHO_UNKNOWN"
    daily_cap = _daily_cap(reading, limits)
    if reading.daily_min + needed_min > daily_cap:
        return "TACHO_DAILY"
    if reading.weekly_min + needed_min > limits.weekly_min:
        return "TACHO_WEEKLY"
    if reading.fortnight_min + needed_min > limits.fortnight_min:
        return "TACHO_FORTNIGHT"
    return None


def uses_extension(reading: Reading, needed_min: int, limits: Limits) -> bool:
    if reading.extensions_used >= limits.extensions:
        return False
    return reading.daily_min + needed_min > limits.daily_min and reading.daily_min + needed_min <= limits.extended_min


def alert_codes(reading: Reading, limits: Limits) -> list[tuple[str, str, int, int]]:
    daily_cap = _daily_cap(reading, limits)
    checks = (
        ("BREAK", reading.continuous_min, limits.continuous_min),
        ("DAILY_DRIVING", reading.daily_min, daily_cap),
        ("WEEKLY_DRIVING", reading.weekly_min, limits.weekly_min),
        ("FORTNIGHT_DRIVING", reading.fortnight_min, limits.fortnight_min),
    )
    found: list[tuple[str, str, int, int]] = []
    for name, measured, limit in checks:
        if measured >= limit:
            code = "BREAK_OVERDUE" if name == "BREAK" else f"{name}_LIMIT"
            found.append((code, "kritik", measured, limit))
        elif measured >= limit - limits.warning_min:
            code = "BREAK_WARNING" if name == "BREAK" else f"{name}_WARNING"
            found.append((code, "uyari", measured, limit))
    if reading.source == "tahmini":
        found.append(("TACHO_ESTIMATED", "uyari", 0, 0))
    return found


def reading_of(state: TachoState | None) -> Reading | None:
    if state is None:
        return None
    return _reading(state)


def drive_minutes(empty_seconds: int, loaded_seconds: int) -> int:
    return max(1, math.ceil((empty_seconds + loaded_seconds) / 60))


def observe(db: Session, vehicle: Vehicle, position: VehiclePosition) -> TachoState | None:
    if vehicle.driver_id is None:
        return None
    previous = (
        db.query(VehiclePosition)
        .filter(VehiclePosition.vehicle_id == vehicle.id, VehiclePosition.id != position.id)
        .order_by(VehiclePosition.recorded_at.desc())
        .first()
    )
    state = db.get(TachoState, vehicle.driver_id)
    if state is None:
        state = TachoState(
            driver_id=vehicle.driver_id,
            tenant_id=vehicle.tenant_id,
            source="tahmini",
            continuous_min=0,
            daily_min=0,
            weekly_min=0,
            fortnight_min=0,
            extensions_used=0,
            split_break_min=0,
            day_key="",
            week_key="",
            fortnight_key="",
        )
        db.add(state)
    _roll_periods(state, position.recorded_at)
    if previous is not None:
        _apply_gap(state, previous, position)
    state.source = "tahmini"
    db.flush()
    return state


def sync_alerts(db: Session, vehicle: Vehicle, settings: TenantSettings) -> None:
    if vehicle.driver_id is None:
        return
    state = db.get(TachoState, vehicle.driver_id)
    if state is None:
        return
    limits = limits_from(settings)
    reading = _reading(state)
    wanted = {code: (level, measured, limit) for code, level, measured, limit in alert_codes(reading, limits)}
    open_load = (
        db.query(Load)
        .filter(Load.vehicle_id == vehicle.id, Load.status.in_(("atandi", "yolda")), Load.planned_drive_min.is_not(None))
        .first()
    )
    if open_load is not None and fit(reading, open_load.planned_drive_min or 0, limits):
        wanted["PLAN_INFEASIBLE"] = ("kritik", open_load.planned_drive_min or 0, _daily_cap(reading, limits) - reading.daily_min)
    existing = db.query(Alert).filter(Alert.tenant_id == vehicle.tenant_id, Alert.vehicle_id == vehicle.id).all()
    by_code = {row.code: row for row in existing}
    for code, (level, measured, limit) in wanted.items():
        row = by_code.get(code)
        if row is None:
            db.add(
                Alert(
                    tenant_id=vehicle.tenant_id,
                    vehicle_id=vehicle.id,
                    driver_id=vehicle.driver_id,
                    code=code,
                    level=level,
                    measured=measured,
                    limit_value=limit,
                )
            )
        else:
            row.level = level
            row.measured = measured
            row.limit_value = limit
    for row in existing:
        if row.code not in wanted:
            db.delete(row)
    if open_load is not None and open_load.locked and "PLAN_INFEASIBLE" in wanted:
        from app.release import break_locked

        break_locked(db, open_load)
    db.flush()


def _daily_cap(reading: Reading, limits: Limits) -> int:
    if reading.extensions_used < limits.extensions:
        return limits.extended_min
    return limits.daily_min


def _reading(state: TachoState) -> Reading:
    return Reading(
        source=state.source,
        continuous_min=state.continuous_min,
        daily_min=state.daily_min,
        weekly_min=state.weekly_min,
        fortnight_min=state.fortnight_min,
        extensions_used=state.extensions_used,
        split_break_min=state.split_break_min,
    )


def _roll_periods(state: TachoState, moment: datetime) -> None:
    day, week, fortnight = _periods(moment)
    if state.day_key and state.day_key != day:
        state.daily_min = 0
    if state.week_key and state.week_key != week:
        state.weekly_min = 0
        state.extensions_used = 0
    if state.fortnight_key and state.fortnight_key != fortnight:
        state.fortnight_min = 0
    state.day_key = day
    state.week_key = week
    state.fortnight_key = fortnight


def _apply_gap(state: TachoState, previous: VehiclePosition, position: VehiclePosition) -> None:
    gap = int((_aware(position.recorded_at) - _aware(previous.recorded_at)).total_seconds() // 60)
    if gap <= 0:
        return
    state.split_break_min = state.split_break_min or 0
    if position.speed_kmh >= DRIVING_SPEED and gap <= SAMPLE_GAP_MIN:
        state.continuous_min += gap
        state.daily_min += gap
        state.weekly_min += gap
        state.fortnight_min += gap
        return
    if gap >= LEGAL_BREAK or (gap >= LEGAL_SPLIT_SECOND and state.split_break_min >= LEGAL_SPLIT_FIRST):
        state.continuous_min = 0
        state.split_break_min = 0
    elif gap >= LEGAL_SPLIT_FIRST and state.split_break_min < LEGAL_SPLIT_FIRST:
        state.split_break_min = LEGAL_SPLIT_FIRST


def _periods(moment: datetime) -> tuple[str, str, str]:
    local = _aware(moment).astimezone(ISTANBUL)
    day = local.date().isoformat()
    monday = local.date() - timedelta(days=local.weekday())
    week_num = monday.isocalendar().week
    return day, monday.isoformat(), f"{monday.isocalendar().year}-{(week_num - 1) // 2}"


def _aware(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)
