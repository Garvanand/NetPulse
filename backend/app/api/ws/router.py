from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from typing import Any
import asyncio
import structlog
from jose import jwt, JWTError

from app.core.config import get_settings

logger = structlog.get_logger()
router = APIRouter(prefix="/ws", tags=["websocket"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("websocket_connected", total_connections=len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("websocket_disconnected", total_connections=len(self.active_connections))

    async def broadcast(self, message: dict[str, Any]):
        for connection in self.active_connections.copy():
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error("websocket_broadcast_error", error=str(e))
                self.disconnect(connection)

manager = ConnectionManager()

@router.websocket("/live")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str | None = Query(None)
):
    """
    WebSocket endpoint for live measurement/incident push updates.
    Expects a JWT token in the query params for authentication.
    """
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
        
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, 
            settings.jwt_secret_key.get_secret_value(), 
            algorithms=[settings.jwt_algorithm]
        )
        if not payload.get("sub"):
            raise JWTError()
    except JWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket)
    try:
        while True:
            # Wait for messages from the client (e.g., ping/pong or filter commands)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
