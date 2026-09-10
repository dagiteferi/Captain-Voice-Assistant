import asyncio
import json
from uuid import UUID

from fastapi.responses import StreamingResponse

_TERMINAL_EVENTS = frozenset({"AudioSynthesized", "PipelineFallback"})


async def stream_events(command_id: UUID, since_event_id: UUID | None = None):
    from main import get_container

    container = get_container()
    repository = container.conversation_repository

    async def event_generator():
        last_id = since_event_id
        for _ in range(120):
            try:
                rows = await repository.list_events_with_ids(command_id, since_event_id=last_id)
                for row in rows:
                    last_id = row["id"]
                    payload = json.loads(row["payload_json"]) if row.get("payload_json") else {}
                    data = json.dumps(
                        {
                            "event_type": row["event_type"],
                            "payload": payload,
                            "occurred_at": row["occurred_at"].isoformat(),
                        }
                    )
                    yield f"event: pipeline_update\ndata: {data}\n\n"
                    if row["event_type"] in _TERMINAL_EVENTS:
                        return
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
