"""Conversation API routes."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Header, status
from pydantic import BaseModel

# Import `get_container` lazily inside handlers to avoid import-time circular imports

router = APIRouter(prefix="/conversations", tags=["conversations"])


class CommandSummary(BaseModel):
    command_id: UUID
    input_text: str
    status: str
    created_at: str


class GetConversationResponse(BaseModel):
    conversation_id: UUID
    captain_id: str
    target_language: str
    created_at: str
    commands: list[CommandSummary]


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: UUID,
    x_user_role: str = Header(...),
) -> GetConversationResponse:
    """Get full conversation history."""
    if x_user_role not in ("captain", "crew"):
        raise HTTPException(status_code=403, detail="Access denied")

    from main import get_container
    container = get_container()
    repository = container.conversation_repository

    conversation = await repository.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    commands = [
        CommandSummary(
            command_id=cmd.id,
            input_text=cmd.input_text,
            status=cmd.status.value,
            created_at=cmd.created_at.isoformat(),
        )
        for cmd in conversation.commands
    ]

    return GetConversationResponse(
        conversation_id=conversation.id,
        captain_id=conversation.captain_id,
        target_language=conversation.target_language.code,
        created_at=conversation.created_at.isoformat(),
        commands=commands,
    )

