from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

import app.arvento as arvento
from app.deps import AppState, get_db, get_state, require_operation_tenant, require_writer
from app.imports import ImportFileError, create_from_form, export_workbook, import_rows, read_table
from app.models import Load, SmsOutbox, TachoState, TenantSettings, User, Vehicle
from app.netgsm import dispatch, drop_pending, poll_reports, queue_event
from app.places import find_place
from app.planning import assignment_for, candidates
from app.returns import solve_returns
from app.schemas import AssignIn, CandidateOut, ImportOut, LoadCreate, LoadOut, LoadRevise, PullOut
from app.tacho import PACK, limits_from

router = APIRouter(tags=["loads"])


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _load_out(db: Session, load: Load, explain: bool = False, api_key: str | None = None) -> LoadOut:
    messages = db.query(SmsOutbox).filter(SmsOutbox.load_id == load.id, SmsOutbox.status != "dustu").all()
    rank = {"iletilemedi": 0, "bekliyor": 1, "kabul": 2, "iletildi": 3}
    event_rank = {"iptal": 0, "guncelleme": 1, "atama": 2}
    sms = min(messages, key=lambda row: (rank.get(row.status, 9), event_rank.get(row.event, 9))) if messages else None
    settings = db.get(TenantSettings, load.tenant_id)
    body = LoadOut.model_validate(load)
    return body.model_copy(
        update={
            "ready_at": _as_utc(load.ready_at),
            "deliver_start": _as_utc(load.deliver_start),
            "deliver_end": _as_utc(load.deliver_end),
            "calculated_at": _as_utc(load.calculated_at) if load.calculated_at else None,
            "sms_status": sms.status if sms else None,
            "sms_job_id": sms.job_id if sms else None,
            "rule_pack": PACK,
            "empty_km_cost": settings.empty_km_cost if settings else None,
            "loaded_km_cost": settings.loaded_km_cost if settings else None,
            "alternatives": _alternatives(db, settings, load, api_key) if explain else [],
            **_tacho_of(db, load, settings),
        }
    )


def _tacho_of(db: Session, load: Load, settings: TenantSettings | None) -> dict:
    if load.vehicle_id is None or settings is None:
        return {}
    vehicle = db.get(Vehicle, load.vehicle_id)
    if vehicle is None or vehicle.driver_id is None:
        return {}
    state = db.get(TachoState, vehicle.driver_id)
    if state is None:
        return {}
    limits = limits_from(settings)
    daily_cap = limits.extended_min if state.extensions_used < limits.extensions else limits.daily_min
    return {
        "tacho_source": state.source,
        "tacho_continuous_min": state.continuous_min,
        "tacho_daily_min": state.daily_min,
        "tacho_weekly_min": state.weekly_min,
        "tacho_continuous_remain": max(0, limits.continuous_min - state.continuous_min),
        "tacho_daily_remain": max(0, daily_cap - state.daily_min),
        "tacho_weekly_remain": max(0, limits.weekly_min - state.weekly_min),
        "tacho_fortnight_remain": max(0, limits.fortnight_min - state.fortnight_min),
    }


def _alternatives(db: Session, settings: TenantSettings | None, load: Load, api_key: str | None) -> list[dict]:
    if settings is None or load.vehicle_id is None:
        return []
    others = (
        db.query(Load)
        .filter(Load.tenant_id == load.tenant_id, Load.id != load.id, Load.status.in_(("havuz", "planlanabilir", "onerildi")))
        .limit(8)
        .all()
    )
    found: list[dict] = []
    for other in others:
        row = next((item for item in candidates(db, settings, other, api_key) if item["vehicle_id"] == load.vehicle_id), None)
        if row is None:
            continue
        if not row["eligible"]:
            found.append({"reference": other.reference, "code": row["code"] or "ELENDI"})
        elif load.benefit_try is not None and row["rank"] is not None and row["rank"] < load.benefit_try:
            found.append({"reference": other.reference, "code": "DUSUK_FAYDA"})
        if len(found) == 3:
            break
    return found


def _apply_revise(load: Load, body: LoadRevise) -> bool:
    changed = False
    if body.pickup_il or body.pickup_ilce:
        place = find_place(body.pickup_il or load.pickup_il, body.pickup_ilce or load.pickup_ilce)
        if place is None:
            raise HTTPException(status_code=422, detail="ROW_PLACE")
        changed = changed or place.il != load.pickup_il or place.ilce != load.pickup_ilce
        load.pickup_il, load.pickup_ilce = place.il, place.ilce
        load.pickup_lat, load.pickup_lng = place.latitude, place.longitude
    if body.drop_il or body.drop_ilce:
        place = find_place(body.drop_il or load.drop_il, body.drop_ilce or load.drop_ilce)
        if place is None:
            raise HTTPException(status_code=422, detail="ROW_PLACE")
        changed = changed or place.il != load.drop_il or place.ilce != load.drop_ilce
        load.drop_il, load.drop_ilce = place.il, place.ilce
        load.drop_lat, load.drop_lng = place.latitude, place.longitude
    for name in ("ready_at", "deliver_start", "deliver_end"):
        value = getattr(body, name)
        if value is None:
            continue
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        if _as_utc(getattr(load, name)) != value.astimezone(UTC):
            changed = True
        setattr(load, name, value.astimezone(UTC))
    if load.deliver_end < load.ready_at or load.deliver_end < load.deliver_start:
        raise HTTPException(status_code=422, detail="ROW_WINDOW")
    return changed


def _load(db: Session, tenant_id: UUID, load_id: UUID) -> Load:
    load = db.get(Load, load_id)
    if load is None or load.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Yük yok")
    return load


@router.get("/loads", response_model=list[LoadOut])
def list_loads(
    direction: str | None = None,
    tenant_id: UUID = Depends(require_operation_tenant),
    db: Session = Depends(get_db),
) -> list[LoadOut]:
    query = db.query(Load).filter(Load.tenant_id == tenant_id)
    if direction in {"gidis", "donus"}:
        query = query.filter(Load.direction == direction)
    rows = query.order_by(Load.ready_at).all()
    return [_load_out(db, row) for row in rows]


@router.get("/loads/export")
def export_loads(
    direction: str | None = None,
    tenant_id: UUID = Depends(require_operation_tenant),
    db: Session = Depends(get_db),
):
    query = db.query(Load).filter(Load.tenant_id == tenant_id, Load.status != "iptal")
    if direction in {"gidis", "donus"}:
        query = query.filter(Load.direction == direction)
    rows = query.order_by(Load.ready_at).all()
    payload = export_workbook(rows)
    name = f"yukler-{direction or 'hepsi'}.xlsx"
    return Response(
        content=payload,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.post("/loads", response_model=LoadOut)
def create_load(
    body: LoadCreate,
    tenant_id: UUID = Depends(require_operation_tenant),
    _: User = Depends(require_writer),
    db: Session = Depends(get_db),
    state: AppState = Depends(get_state),
) -> LoadOut:
    from app.routers.fleet import _settings

    settings = _settings(db, tenant_id)
    code, load = create_from_form(
        db,
        tenant_id,
        settings,
        body.model_dump(),
        state.settings.google_maps_server_key,
    )
    if code or load is None:
        raise HTTPException(status_code=422, detail=code or "ROW_REQUIRED")
    if load.direction == "donus":
        solve_returns(db, tenant_id, settings, state.settings.google_maps_server_key, state.settings)
    else:
        db.commit()
    db.refresh(load)
    return _load_out(db, load)


@router.get("/loads/{load_id}", response_model=LoadOut)
def read_load(
    load_id: UUID,
    tenant_id: UUID = Depends(require_operation_tenant),
    db: Session = Depends(get_db),
    state: AppState = Depends(get_state),
) -> LoadOut:
    load = _load(db, tenant_id, load_id)
    return _load_out(db, load, explain=True, api_key=state.settings.google_maps_server_key)


@router.delete("/loads/{load_id}", response_model=LoadOut)
def remove_load(
    load_id: UUID,
    tenant_id: UUID = Depends(require_operation_tenant),
    _: User = Depends(require_writer),
    db: Session = Depends(get_db),
    state: AppState = Depends(get_state),
) -> LoadOut:
    load = _load(db, tenant_id, load_id)
    if load.status in {"teslim", "yolda", "iptal"}:
        raise HTTPException(status_code=409, detail="LOAD_NOT_READY")
    if load.status == "atandi":
        return cancel_load(load_id, tenant_id, _, db, state)
    drop_pending(db, load.id)
    load.status = "iptal"
    load.vehicle_id = None
    load.locked = False
    load.uses_extension = False
    db.commit()
    db.refresh(load)
    return _load_out(db, load)


@router.post("/loads/import", response_model=ImportOut)
async def import_loads(
    file: UploadFile = File(...),
    tenant_id: UUID = Depends(require_operation_tenant),
    _: User = Depends(require_writer),
    db: Session = Depends(get_db),
    state: AppState = Depends(get_state),
) -> dict:
    raw = await file.read()
    try:
        rows = read_table(file.filename or "yuk.csv", raw)
    except ImportFileError as exc:
        raise HTTPException(status_code=422, detail=exc.code) from exc
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="FILE_COLUMNS") from exc
    from app.routers.fleet import _settings

    settings = _settings(db, tenant_id)
    result = import_rows(db, tenant_id, settings, rows, state.settings.google_maps_server_key)
    solve_returns(db, tenant_id, settings, state.settings.google_maps_server_key, state.settings)
    return result


@router.get("/loads/{load_id}/candidates", response_model=list[CandidateOut])
def load_candidates(
    load_id: UUID,
    tenant_id: UUID = Depends(require_operation_tenant),
    db: Session = Depends(get_db),
    state: AppState = Depends(get_state),
) -> list[dict]:
    load = _load(db, tenant_id, load_id)
    from app.routers.fleet import _settings

    return candidates(db, _settings(db, tenant_id), load, state.settings.google_maps_server_key)


@router.post("/loads/{load_id}/assign", response_model=LoadOut)
def assign_load(
    load_id: UUID,
    body: AssignIn,
    tenant_id: UUID = Depends(require_operation_tenant),
    _: User = Depends(require_writer),
    db: Session = Depends(get_db),
    state: AppState = Depends(get_state),
) -> LoadOut:
    load = _load(db, tenant_id, load_id)
    if load.direction != "gidis" or load.status != "planlanabilir":
        raise HTTPException(status_code=409, detail="LOAD_NOT_READY")
    vehicle = db.get(Vehicle, body.vehicle_id)
    if vehicle is None or vehicle.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Araç yok")
    from app.routers.fleet import _settings

    try:
        chosen = assignment_for(db, _settings(db, tenant_id), load, vehicle, state.settings.google_maps_server_key)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    load.vehicle_id = vehicle.id
    load.status = "atandi"
    load.empty_km = chosen["empty_km"]
    load.loaded_km = chosen["loaded_km"]
    load.distance_quality = chosen["distance_quality"]
    load.rank_value = chosen["rank"]
    load.planned_drive_min = chosen["drive_min"]
    load.planned_break_min = chosen["break_min"]
    load.calculated_at = datetime.now(UTC)
    load.uses_extension = bool(chosen["uses_extension"])
    if load.uses_extension and vehicle.driver_id is not None:
        counter = db.get(TachoState, vehicle.driver_id)
        if counter is not None:
            counter.extensions_used += 1
    queue_event(db, tenant_id, load, vehicle, "atama")
    dispatch(db, tenant_id, state.settings)
    db.commit()
    db.refresh(load)
    return _load_out(db, load)


@router.post("/loads/{load_id}/cancel", response_model=LoadOut)
def cancel_load(
    load_id: UUID,
    tenant_id: UUID = Depends(require_operation_tenant),
    _: User = Depends(require_writer),
    db: Session = Depends(get_db),
    state: AppState = Depends(get_state),
) -> LoadOut:
    load = _load(db, tenant_id, load_id)
    if load.status != "atandi":
        raise HTTPException(status_code=409, detail="LOAD_NOT_READY")
    if load.uses_extension and load.vehicle_id is not None:
        bound = db.get(Vehicle, load.vehicle_id)
        if bound is not None and bound.driver_id is not None:
            counter = db.get(TachoState, bound.driver_id)
            if counter is not None:
                counter.extensions_used = max(0, counter.extensions_used - 1)
    vehicle = db.get(Vehicle, load.vehicle_id) if load.vehicle_id else None
    if load.locked and vehicle is not None:
        queue_event(db, tenant_id, load, vehicle, "iptal")
        dispatch(db, tenant_id, state.settings)
    else:
        drop_pending(db, load.id)
    load.status = "iptal"
    load.vehicle_id = None
    load.uses_extension = False
    load.locked = False
    db.commit()
    db.refresh(load)
    return _load_out(db, load)


@router.post("/loads/{load_id}/revise", response_model=LoadOut)
def revise_load(
    load_id: UUID,
    body: LoadRevise,
    tenant_id: UUID = Depends(require_operation_tenant),
    _: User = Depends(require_writer),
    db: Session = Depends(get_db),
    state: AppState = Depends(get_state),
) -> LoadOut:
    load = _load(db, tenant_id, load_id)
    if load.status not in {"atandi", "onerildi"} or load.vehicle_id is None:
        raise HTTPException(status_code=409, detail="LOAD_NOT_READY")
    changed = _apply_revise(load, body)
    vehicle = db.get(Vehicle, load.vehicle_id)
    if changed and vehicle is not None and load.status == "atandi":
        queue_event(db, tenant_id, load, vehicle, "guncelleme")
        dispatch(db, tenant_id, state.settings)
    db.commit()
    db.refresh(load)
    return _load_out(db, load)


@router.post("/loads/{load_id}/approve", response_model=LoadOut)
def approve_load(
    load_id: UUID,
    tenant_id: UUID = Depends(require_operation_tenant),
    _: User = Depends(require_writer),
    db: Session = Depends(get_db),
    state: AppState = Depends(get_state),
) -> LoadOut:
    load = _load(db, tenant_id, load_id)
    if load.status != "onerildi" or load.vehicle_id is None:
        raise HTTPException(status_code=409, detail="LOAD_NOT_READY")
    vehicle = db.get(Vehicle, load.vehicle_id)
    load.status = "atandi"
    if vehicle is not None:
        queue_event(db, tenant_id, load, vehicle, "atama")
        dispatch(db, tenant_id, state.settings)
    db.commit()
    db.refresh(load)
    return _load_out(db, load)


@router.post("/loads/{load_id}/deliver", response_model=LoadOut)
def deliver_load(
    load_id: UUID,
    tenant_id: UUID = Depends(require_operation_tenant),
    _: User = Depends(require_writer),
    db: Session = Depends(get_db),
    state: AppState = Depends(get_state),
) -> LoadOut:
    load = _load(db, tenant_id, load_id)
    if load.status not in {"atandi", "yolda"}:
        raise HTTPException(status_code=409, detail="LOAD_NOT_READY")
    load.status = "teslim"
    from app.routers.fleet import _settings

    solve_returns(db, tenant_id, _settings(db, tenant_id), state.settings.google_maps_server_key, state.settings)
    db.refresh(load)
    return _load_out(db, load)


@router.post("/loads/{load_id}/sms/resend", response_model=LoadOut)
def resend_sms(
    load_id: UUID,
    tenant_id: UUID = Depends(require_operation_tenant),
    _: User = Depends(require_writer),
    db: Session = Depends(get_db),
    state: AppState = Depends(get_state),
) -> LoadOut:
    load = _load(db, tenant_id, load_id)
    if load.vehicle_id is None or load.status not in {"atandi", "onerildi"}:
        raise HTTPException(status_code=409, detail="LOAD_NOT_READY")
    failed = db.query(SmsOutbox).filter(SmsOutbox.load_id == load.id, SmsOutbox.status == "iletilemedi").all()
    if not failed:
        raise HTTPException(status_code=409, detail="SMS_NOT_FAILED")
    vehicle = db.get(Vehicle, load.vehicle_id)
    events = list(dict.fromkeys(row.event for row in failed))
    for row in failed:
        row.status = "dustu"
    db.flush()
    if vehicle is not None:
        for event in events:
            queue_event(db, tenant_id, load, vehicle, event)
        dispatch(db, tenant_id, state.settings)
    db.commit()
    db.refresh(load)
    return _load_out(db, load)


@router.post("/sms/report")
def read_reports(
    tenant_id: UUID = Depends(require_operation_tenant),
    _: User = Depends(require_writer),
    db: Session = Depends(get_db),
    state: AppState = Depends(get_state),
) -> dict:
    updated = poll_reports(db, tenant_id, state.settings)
    db.commit()
    return {"updated": updated}


@router.post("/returns/solve")
def solve_pool(
    tenant_id: UUID = Depends(require_operation_tenant),
    _: User = Depends(require_writer),
    db: Session = Depends(get_db),
    state: AppState = Depends(get_state),
) -> dict:
    from app.routers.fleet import _settings

    count = solve_returns(db, tenant_id, _settings(db, tenant_id), state.settings.google_maps_server_key, state.settings)
    return {"assigned": count}


@router.post("/integrations/arvento/pull", response_model=PullOut)
def pull_arvento(
    tenant_id: UUID = Depends(require_operation_tenant),
    _: User = Depends(require_writer),
    db: Session = Depends(get_db),
    state: AppState = Depends(get_state),
) -> PullOut:
    try:
        username, pin1, pin2 = arvento.credentials(db, tenant_id, state.settings)
        packets = arvento.fetch_packets(username, pin1, pin2)
    except arvento.MissingSecret as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except arvento.ArventoError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    updated, unmatched = arvento.apply_packets(db, tenant_id, packets)
    dispatch(db, tenant_id, state.settings)
    db.commit()
    return PullOut(updated=updated, unmatched=unmatched)
