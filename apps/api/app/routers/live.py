from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.deps import AppState, get_current_user, get_db, get_state, require_operation_tenant
from app.live import hub
from app.models import User
from app.security import decode_token
from app.tracking import snapshot

router = APIRouter(tags=["live"])


@router.get("/live/snapshot")
def live_snapshot(
    tenant_id: UUID = Depends(require_operation_tenant),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    return {"type": "snapshot", "vehicles": snapshot(db, tenant_id)}


@router.get("/live/config")
def live_config(
    user: User = Depends(get_current_user),
    state: AppState = Depends(get_state),
) -> dict:
    if user.role == "platform_admin" or user.tenant_id is None:
        raise HTTPException(status_code=403, detail="Platform yöneticisi canlı haritayı açamaz")
    return {
        "supabase": state.settings.supabase_enabled,
        "supabase_url": state.settings.supabase_url if state.settings.supabase_enabled else None,
        "channel": f"tenant:{user.tenant_id}" if state.settings.supabase_enabled else None,
        "anon_key": state.settings.supabase_anon_key if state.settings.supabase_enabled else None,
    }


@router.websocket("/live")
async def live_map(websocket: WebSocket, token: str = Query(default="")) -> None:
    state: AppState = websocket.app.state.runtime
    db = state.factory()
    try:
        user = _operator(state, db, token)
        tenant_id = user.tenant_id
    except PermissionError:
        await websocket.accept()
        await websocket.close(code=1008)
        return
    finally:
        db.close()
    if tenant_id is None:
        await websocket.accept()
        await websocket.close(code=1008)
        return
    await hub.connect(tenant_id, websocket)
    db = state.factory()
    try:
        await websocket.send_json({"type": "snapshot", "vehicles": snapshot(db, tenant_id)})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        db.close()
        hub.disconnect(tenant_id, websocket)


def _operator(state: AppState, db: Session, token: str) -> User:
    if not token:
        raise PermissionError
    try:
        payload = decode_token(state.settings, token)
        user_id = UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise PermissionError from exc
    user = db.get(User, user_id)
    if user is None or not user.active or user.role == "platform_admin" or user.tenant_id is None:
        raise PermissionError
    if state.settings.deployment_mode == "dedicated":
        expected = UUID(state.settings.tenant_id or "")
        if user.tenant_id != expected:
            raise PermissionError
    return user
