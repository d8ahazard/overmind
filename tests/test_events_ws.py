import asyncio

from app.core.events import Event, EventBus


def test_event_bus_publish():
    bus = EventBus()
    queue = bus.subscribe()

    async def run():
        await bus.publish(Event(type="test", payload={"ok": True}))
        message = await queue.get()
        assert '"type": "test"' in message

    asyncio.run(run())
