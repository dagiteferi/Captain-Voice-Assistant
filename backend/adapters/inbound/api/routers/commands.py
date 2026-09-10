"""Command API routes."""

from fastapi import APIRouter

router = APIRouter(prefix="/commands", tags=["commands"])


@router.post("")
async def submit_command():
    return {"status": "accepted"}
