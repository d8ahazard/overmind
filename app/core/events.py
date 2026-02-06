import asyncio
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class Event:
    type: str
    payload: Dict[str, Any]
    timestamp: str = datetime.utcnow().isoformat()

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=True)


class EventBus:
    def __init__(self) -> None:
        self._subscribers: List[asyncio.Queue[str]] = []

    def subscribe(self) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue()
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[str]) -> None:
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    async def publish(self, event: Event) -> None:
        message = event.to_json()
        for queue in list(self._subscribers):
            await queue.put(message)
