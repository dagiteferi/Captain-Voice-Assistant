"""Server-sent events support for live pipeline trace updates."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/events")
async def events_stream():
    return {"status": "streaming"}
