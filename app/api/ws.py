from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.events import EventBus

router = APIRouter()


@router.websocket("/events")
async def events_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    event_bus: EventBus = websocket.app.state.event_bus
    queue = event_bus.subscribe()
    try:
        await websocket.send_text('{"type":"connection.ready","payload":{}}')
        while True:
            message = await queue.get()
            await websocket.send_text(message)
    except WebSocketDisconnect:
        event_bus.unsubscribe(queue)
