import asyncio
from uuid import UUID

from fastapi import WebSocket


class LiveHub:
    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._rooms: dict[UUID, set[WebSocket]] = {}

    def bind(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, tenant_id: UUID, socket: WebSocket) -> None:
        await socket.accept()
        self._rooms.setdefault(tenant_id, set()).add(socket)

    def disconnect(self, tenant_id: UUID, socket: WebSocket) -> None:
        room = self._rooms.get(tenant_id)
        if room is None:
            return
        room.discard(socket)
        if not room:
            self._rooms.pop(tenant_id, None)

    def publish(self, tenant_id: UUID, message: dict) -> None:
        loop = self._loop
        if loop is None or loop.is_closed():
            return
        try:
            asyncio.run_coroutine_threadsafe(self._send(tenant_id, message), loop)
        except RuntimeError:
            return

    async def _send(self, tenant_id: UUID, message: dict) -> None:
        dead: list[WebSocket] = []
        for socket in list(self._rooms.get(tenant_id, ())):
            try:
                await socket.send_json(message)
            except Exception:
                dead.append(socket)
        for socket in dead:
            self.disconnect(tenant_id, socket)


hub = LiveHub()
