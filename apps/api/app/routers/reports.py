from datetime import date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.deps import get_db, require_operation_tenant
from app.reports import SLUGS, TITLES, build_report, export_report
from app.schemas import ReportOut

router = APIRouter(tags=["reports"])
ISTANBUL = ZoneInfo("Europe/Istanbul")


@router.get("/reports", response_model=list[dict])
def list_reports(tenant_id: UUID = Depends(require_operation_tenant)) -> list[dict]:
    _ = tenant_id
    return [{"slug": slug, "title": TITLES[slug]} for slug in SLUGS]


@router.get("/reports/{slug}", response_model=ReportOut)
def read_report(
    slug: str,
    from_day: date | None = Query(default=None, alias="from"),
    to_day: date | None = Query(default=None, alias="to"),
    direction: str | None = None,
    tenant_id: UUID = Depends(require_operation_tenant),
    db: Session = Depends(get_db),
) -> ReportOut:
    start, end = _range(from_day, to_day)
    try:
        return build_report(db, tenant_id, slug, start, end, direction)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/reports/{slug}/export")
def export_report_file(
    slug: str,
    from_day: date | None = Query(default=None, alias="from"),
    to_day: date | None = Query(default=None, alias="to"),
    direction: str | None = None,
    tenant_id: UUID = Depends(require_operation_tenant),
    db: Session = Depends(get_db),
) -> Response:
    start, end = _range(from_day, to_day)
    try:
        payload = export_report(db, tenant_id, slug, start, end, direction)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    name = f"{slug}-{start.isoformat()}-{end.isoformat()}.xlsx"
    return Response(
        content=payload,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


def _range(from_day: date | None, to_day: date | None) -> tuple[date, date]:
    today = datetime.now(ISTANBUL).date()
    end = to_day or today
    start = from_day or (end - timedelta(days=29))
    if start > end:
        raise HTTPException(status_code=422, detail="Tarih aralığı ters")
    if (end - start).days > 366:
        raise HTTPException(status_code=422, detail="En fazla 366 gün")
    return start, end
