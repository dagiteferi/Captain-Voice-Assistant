"""Conversation API routes."""

from fastapi import APIRouter

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str):
    return {"conversation_id": conversation_id, "status": "ok"}
