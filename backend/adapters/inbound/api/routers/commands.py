"""Command API routes."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Header, status
from pydantic import BaseModel

# Import `get_container` lazily inside handlers to avoid import-time circular imports
from domain.conversation.entities import Conversation, Command
from domain.conversation.value_objects import Language

router = APIRouter(prefix="/commands", tags=["commands"])


class SubmitCommandRequest(BaseModel):
    conversation_id: UUID | None = None
    input_text: str
    target_language: str


class CommandResponse(BaseModel):
    command_id: UUID
    conversation_id: UUID
    status: str


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def submit_command(
    request: SubmitCommandRequest,
    x_user_role: str = Header(...),
) -> CommandResponse:
    """Submit a new captain/crew command."""
    if x_user_role not in ("captain", "crew"):
        raise HTTPException(status_code=403, detail="Only captain and crew can submit commands")

    from main import get_container
    container = get_container()
    repository = container.conversation_repository

    conversation_id = request.conversation_id
    if conversation_id is None:
        # Create a new conversation
        conversation = Conversation(
            captain_id=x_user_role,
            target_language=Language(request.target_language),
        )
        await repository.save_conversation(conversation)
        conversation_id = conversation.id
    else:
        # Load existing conversation
        conversation = await repository.get_conversation(conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")

    # Create and run command through orchestrator
    command = Command(
        conversation_id=conversation_id,
        input_text=request.input_text,
    )
    await repository.save_command(command)

    # Kick off async orchestration (in real impl, would queue this)
    # For now, execute synchronously for dev
    try:
        await container.orchestrator.execute(command)
    except Exception as e:
        command.mark_failed()
        await repository.save_command(command)
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")

    return CommandResponse(
        command_id=command.id,
        conversation_id=conversation_id,
        status=command.status.value,
    )


class CitationModel(BaseModel):
    chunk_id: UUID
    document_title: str | None = None
    similarity_score: float | None = None


class GetCommandResponse(BaseModel):
    command_id: UUID
    conversation_id: UUID
    status: str
    input_text: str
    answer_text: str | None = None
    citations: list[CitationModel] = []
    translated_text: str | None = None
    target_language: str
    audio_url: str | None = None
    created_at: str
    completed_at: str | None = None


@router.get("/{command_id}")
async def get_command(
    command_id: UUID,
    x_user_role: str = Header(...),
) -> GetCommandResponse:
    """Get command status and result."""
    if x_user_role not in ("captain", "crew"):
        raise HTTPException(status_code=403, detail="Access denied")

    from main import get_container
    container = get_container()
    repository = container.conversation_repository

    command = await repository.get_command(command_id)
    if command is None:
        raise HTTPException(status_code=404, detail="Command not found")

    citations = []
    if command.grounded_answer:
        citations = [
            CitationModel(chunk_id=c.chunk_id, similarity_score=0.0)
            for c in command.grounded_answer.citations
        ]

    answer_text = command.grounded_answer.answer_text if command.grounded_answer else None

    return GetCommandResponse(
        command_id=command.id,
        conversation_id=command.conversation_id,
        status=command.status.value,
        input_text=command.input_text,
        answer_text=answer_text,
        citations=citations,
        translated_text=None,
        target_language="en",
        audio_url=None,
        created_at=command.created_at.isoformat(),
        completed_at=None,
    )


class TraceEventModel(BaseModel):
    event_type: str
    payload: dict
    occurred_at: str


class TraceResponse(BaseModel):
    command_id: UUID
    events: list[TraceEventModel]


@router.get("/{command_id}/trace")
async def get_command_trace(
    command_id: UUID,
    x_user_role: str = Header(...),
) -> TraceResponse:
    """Get full pipeline trace for command."""
    if x_user_role not in ("captain", "crew"):
        raise HTTPException(status_code=403, detail="Access denied")

    from main import get_container
    container = get_container()
    repository = container.conversation_repository

    events = await repository.list_events(command_id)

    trace_events = []
    for event in events:
        event_type = type(event).__name__
        # Simple payload extraction
        payload = {
            "event_type": event_type,
        }
        trace_events.append(TraceEventModel(
            event_type=event_type,
            payload=payload,
            occurred_at=event.occurred_at.isoformat(),
        ))

    return TraceResponse(command_id=command_id, events=trace_events)


@router.get("/{command_id}/stream")
async def stream_command_trace(command_id: UUID, x_user_role: str = Header(...)):
    """Stream pipeline trace as SSE."""
    if x_user_role not in ("captain", "crew"):
        raise HTTPException(status_code=403, detail="Access denied")

    from adapters.inbound.api.sse import stream_events
    return stream_events(command_id)

