from sqlalchemy.orm import Session

from app.models import Load, TachoState, Vehicle
from app.netgsm import drop_pending, queue_event


def break_locked(db: Session, load: Load) -> bool:
    if not load.locked or load.vehicle_id is None or load.status not in {"atandi", "yolda"}:
        return False
    vehicle = db.get(Vehicle, load.vehicle_id)
    if load.uses_extension and vehicle is not None and vehicle.driver_id is not None:
        counter = db.get(TachoState, vehicle.driver_id)
        if counter is not None:
            counter.extensions_used = max(0, counter.extensions_used - 1)
    drop_pending(db, load.id)
    if vehicle is not None:
        queue_event(db, load.tenant_id, load, vehicle, "iptal")
    load.vehicle_id = None
    load.locked = False
    load.uses_extension = False
    load.status = "havuz" if load.direction == "donus" else "planlanabilir"
    return True
