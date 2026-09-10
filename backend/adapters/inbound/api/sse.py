"""Server-sent events support for live pipeline trace updates."""

import asyncio
import json
from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()


async def stream_events(command_id: UUID):
    """Stream pipeline events as SSE."""
    from main import get_container

    container = get_container()
    repository = container.conversation_repository

    async def event_generator():
        # Polling-based streaming for now
        # In production, would use proper event subscription
        seen_events = set()

        for _ in range(60):  # Poll for up to 60 seconds
            try:
                events = await repository.list_events(command_id)
                for event in events:
                    event_id = id(event)
                    if event_id not in seen_events:
                        seen_events.add(event_id)
                        event_type = type(event).__name__
                        payload = {}  # Simplified
                        data = json.dumps({
                            "event_type": event_type,
                            "payload": payload,
                            "occurred_at": event.occurred_at.isoformat(),
                        })
                        yield f"event: pipeline_update\ndata: {data}\n\n"
            except Exception:
                pass

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

