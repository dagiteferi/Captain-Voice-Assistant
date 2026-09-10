"""Server-sent events support for live pipeline trace updates."""

import asyncio
import json
from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from uuid import UUID as _UUID
import json as _json

router = APIRouter()


async def stream_events(command_id: UUID, since_event_id: _UUID | None = None):
    """Stream pipeline events as SSE."""
    from main import get_container
    container = get_container()
    repository = container.conversation_repository

    async def event_generator():
        # Poll the persisted events ordered by occurred_at, id. Use since_event_id
        # to resume without replaying already-seen events.
        last_id = since_event_id

        for _ in range(120):  # poll for up to ~60 seconds (0.5s sleep)
            try:
                rows = await repository.list_events_with_ids(command_id, since_event_id=last_id)
                for row in rows:
                    # row: {id, event_type, payload_json, occurred_at}
                    last_id = row["id"]
                    payload = _json.loads(row["payload_json"]) if row.get("payload_json") else {}
                    data = _json.dumps(
                        {
                            "event_type": row["event_type"],
                            "payload": payload,
                            "occurred_at": row["occurred_at"].isoformat(),
                        }
                    )
                    yield f"event: pipeline_update\ndata: {data}\n\n"
            except Exception:
                # swallow transient errors and continue polling
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

