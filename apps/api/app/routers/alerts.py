from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import get_db, require_operation_tenant, require_writer
from app.models import Alert, User
from app.schemas import AlertOut

router = APIRouter(tags=["alerts"])


@router.get("/alerts", response_model=list[AlertOut])
def list_alerts(tenant_id: UUID = Depends(require_operation_tenant), db: Session = Depends(get_db)) -> list[Alert]:
    return (
        db.query(Alert)
        .filter(Alert.tenant_id == tenant_id)
        .order_by(Alert.level, Alert.code)
        .all()
    )


@router.post("/alerts/{alert_id}/seen", response_model=AlertOut)
def see_alert(
    alert_id: UUID,
    tenant_id: UUID = Depends(require_operation_tenant),
    _: User = Depends(require_writer),
    db: Session = Depends(get_db),
) -> Alert:
    row = db.get(Alert, alert_id)
    if row is None or row.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Uyarı yok")
    row.seen_at = datetime.now(UTC)
    db.commit()
    db.refresh(row)
    return row
