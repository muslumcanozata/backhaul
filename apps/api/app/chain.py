"""Ardışık yük zinciri için takograf simülasyonu ve sürücü tavsiyesi.

Saf fonksiyonlar. Veritabanına ve ağa dokunmaz. Konum önermez, yalnız zaman hesaplar."""

from dataclasses import dataclass, replace

from app.tacho import LEGAL_BREAK, Limits, Reading

DAILY_REST_MIN = 11 * 60


@dataclass(frozen=True)
class Step:
    kind: str  # drive, break, rest
    minutes: int
    after_drive_min: int  # bu adımdan önce simülasyonda sürülen toplam dakika


@dataclass(frozen=True)
class Simulation:
    code: str | None
    elapsed_min: int
    drive_min: int
    break_min: int
    rest_count: int
    steps: tuple[Step, ...]
    end: Reading
    day_extended: bool


def simulate(reading: Reading, drive_legs: list[int], limits: Limits, day_extended: bool | None = None) -> Simulation:
    """Sürüş bacaklarını sırayla yürütür. 4,5 saatte mola, günlük sınırda günlük dinlenme ekler.
    Haftalık veya iki haftalık sınır aşılırsa uygulanamaz (TACHO_WEEKLY, TACHO_FORTNIGHT)."""
    current = reading
    extended = reading.daily_min > limits.daily_min if day_extended is None else day_extended
    steps: list[Step] = []
    driven = 0
    elapsed = 0
    breaks = 0
    rests = 0
    for leg in drive_legs:
        left = max(int(leg), 0)
        guard = 0
        while left > 0:
            guard += 1
            if guard > 200:
                return _result("TACHO_UNKNOWN", elapsed, driven, breaks, rests, steps, current, extended)
            if current.weekly_min >= limits.weekly_min:
                return _result("TACHO_WEEKLY", elapsed, driven, breaks, rests, steps, current, extended)
            if current.fortnight_min >= limits.fortnight_min:
                return _result("TACHO_FORTNIGHT", elapsed, driven, breaks, rests, steps, current, extended)
            cap = _cap(current, limits, extended)
            if current.daily_min >= cap:
                steps.append(Step("rest", DAILY_REST_MIN, driven))
                elapsed += DAILY_REST_MIN
                rests += 1
                current = replace(current, continuous_min=0, daily_min=0, split_break_min=0)
                extended = False
                continue
            if current.continuous_min >= limits.continuous_min:
                steps.append(Step("break", LEGAL_BREAK, driven))
                elapsed += LEGAL_BREAK
                breaks += LEGAL_BREAK
                current = replace(current, continuous_min=0, split_break_min=0)
                continue
            chunk = min(
                left,
                limits.continuous_min - current.continuous_min,
                cap - current.daily_min,
                limits.weekly_min - current.weekly_min,
                limits.fortnight_min - current.fortnight_min,
            )
            if chunk <= 0:
                return _result("TACHO_UNKNOWN", elapsed, driven, breaks, rests, steps, current, extended)
            before = current.daily_min
            current = replace(
                current,
                continuous_min=current.continuous_min + chunk,
                daily_min=current.daily_min + chunk,
                weekly_min=current.weekly_min + chunk,
                fortnight_min=current.fortnight_min + chunk,
            )
            if not extended and before + chunk > limits.daily_min:
                extended = True
                current = replace(current, extensions_used=current.extensions_used + 1)
            driven += chunk
            elapsed += chunk
            left -= chunk
    return _result(None, elapsed, driven, breaks, rests, steps, current, extended)


def _cap(reading: Reading, limits: Limits, extended: bool) -> int:
    if extended or reading.extensions_used < limits.extensions:
        return limits.extended_min
    return limits.daily_min


def _result(code, elapsed, driven, breaks, rests, steps, current, extended) -> Simulation:
    return Simulation(code, elapsed, driven, breaks, rests, tuple(steps), current, extended)


def format_minutes(minutes: int) -> str:
    minutes = max(int(minutes), 0)
    hours, rest = divmod(minutes, 60)
    if hours and rest:
        return f"{hours} saat {rest} dk"
    if hours:
        return f"{hours} saat"
    return f"{rest} dk"


def advice_lines(sim: Simulation, limits: Limits) -> list[str]:
    """Sürücüye takograf süresine göre zaman tavsiyesi. Konum içermez."""
    if sim.code is not None:
        return []
    lines: list[str] = []
    for step in sim.steps:
        if step.kind == "break":
            when = f"{format_minutes(step.after_drive_min)} sürüşten sonra" if step.after_drive_min else "Hemen"
            lines.append(f"{when} {step.minutes} dk mola ver.")
        elif step.kind == "rest":
            when = f"{format_minutes(step.after_drive_min)} sürüşten sonra" if step.after_drive_min else "Hemen"
            lines.append(f"{when} günlük dinlenme gerekir ({format_minutes(step.minutes)}).")
    cap = _cap(sim.end, limits, sim.day_extended)
    remain = max(cap - sim.end.daily_min, 0)
    lines.append(f"Bu sürüşün sonunda günlük sürüşe {format_minutes(remain)} kalır.")
    return lines
