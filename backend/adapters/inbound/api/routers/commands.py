from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Query, status
from pydantic import BaseModel

from domain.conversation.entities import Command, Conversation
from domain.conversation.value_objects import Language

router = APIRouter(prefix="/commands", tags=["commands"])


class SubmitCommandRequest(BaseModel):
    conversation_id: UUID | None = None
    input_text: str
    target_language: str
    voice_id: str | None = None


class CommandResponse(BaseModel):
    command_id: UUID
    conversation_id: UUID
    status: str


def _require_operator(role: str) -> None:
    if role not in ("captain", "crew"):
        raise HTTPException(status_code=403, detail="Only captain and crew can submit commands")


async def _run_pipeline(command_id: UUID) -> None:
    from main import get_container

    container = get_container()
    command = await container.conversation_repository.get_command(command_id)
    if command is None:
        return
    try:
        await container.orchestrator.execute(command)
    except Exception:
        command.mark_failed()
        await container.conversation_repository.save_command(command)


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def submit_command(
    request: SubmitCommandRequest,
    background_tasks: BackgroundTasks,
    x_user_role: str = Header(...),
) -> CommandResponse:
    _require_operator(x_user_role)

    from main import get_container

    container = get_container()
    repository = container.conversation_repository

    conversation_id = request.conversation_id
    if conversation_id is None:
        conversation = Conversation(
            captain_id=x_user_role,
            target_language=Language(request.target_language),
        )
        await repository.save_conversation(conversation)
        conversation_id = conversation.id
    else:
        conversation = await repository.get_conversation(conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")

    command = Command(
        conversation_id=conversation_id,
        input_text=request.input_text,
        voice_id=request.voice_id,
    )
    await repository.save_command(command)
    background_tasks.add_task(_run_pipeline, command.id)

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
    if x_user_role not in ("captain", "crew"):
        raise HTTPException(status_code=403, detail="Access denied")

    from main import get_container

    container = get_container()
    repository = container.conversation_repository

    command = await repository.get_command(command_id)
    if command is None:
        raise HTTPException(status_code=404, detail="Command not found")

    conversation = await repository.get_conversation(command.conversation_id)
    target_language = conversation.target_language.code if conversation else "en"

    citations = []
    if command.grounded_answer:
        citations = [
            CitationModel(chunk_id=c.chunk_id, similarity_score=None, document_title=None)
            for c in command.grounded_answer.citations
        ]

    answer_text = command.grounded_answer.answer_text if command.grounded_answer else None
    translated_text = None
    audio_url = None
    if command.grounded_answer:
        translation = await repository.get_translation_for_answer(command.grounded_answer.id)
        if translation:
            translated_text = translation.translated_text
            audio = await repository.get_audio_for_translation(translation.id)
            if audio:
                audio_url = f"/api/v1/audio/{audio.id}"

    completed_at = None
    if command.status.value != "pending":
        events = await repository.list_events(command_id)
        if events:
            completed_at = events[-1].occurred_at.isoformat()

    return GetCommandResponse(
        command_id=command.id,
        conversation_id=command.conversation_id,
        status=command.status.value,
        input_text=command.input_text,
        answer_text=answer_text,
        citations=citations,
        translated_text=translated_text,
        target_language=target_language,
        audio_url=audio_url,
        created_at=command.created_at.isoformat(),
        completed_at=completed_at,
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
    if x_user_role not in ("captain", "crew"):
        raise HTTPException(status_code=403, detail="Access denied")

    from main import get_container
    import json

    container = get_container()
    repository = container.conversation_repository

    command = await repository.get_command(command_id)
    if command is None:
        raise HTTPException(status_code=404, detail="Command not found")

    rows = await repository.list_events_with_ids(command_id)
    trace_events = []
    for row in rows:
        payload = {}
        try:
            payload = json.loads(row["payload_json"]) if row.get("payload_json") else {}
        except Exception:
            payload = {}
        trace_events.append(
            TraceEventModel(
                event_type=row["event_type"],
                payload=payload,
                occurred_at=row["occurred_at"].isoformat(),
            )
        )

    return TraceResponse(command_id=command_id, events=trace_events)


@router.get("/{command_id}/stream")
async def stream_command_trace(
    command_id: UUID,
    x_user_role: str = Header(...),
    since_event_id: UUID | None = Query(None, alias="since_event_id"),
):
    if x_user_role not in ("captain", "crew"):
        raise HTTPException(status_code=403, detail="Access denied")

    from main import get_container

    container = get_container()
    command = await container.conversation_repository.get_command(command_id)
    if command is None:
        raise HTTPException(status_code=404, detail="Command not found")

    from adapters.inbound.api.sse import stream_events

    return await stream_events(command_id, since_event_id=since_event_id)


class RetranslateRequest(BaseModel):
    target_language: str
    voice_id: str | None = None

@router.post("/{command_id}/retranslate")
async def retranslate_command(
    command_id: UUID,
    request: RetranslateRequest,
    x_user_role: str = Header(...),
):
    if x_user_role not in ("captain", "crew"):
        raise HTTPException(status_code=403, detail="Access denied")

    from main import get_container
    from domain.voice.entities import Translation, AudioResponse, CAPTAIN_PRESET
    from domain.conversation.value_objects import Language
    import uuid
    import os
    
    container = get_container()
    command = await container.conversation_repository.get_command(command_id)
    if command is None or not command.grounded_answer:
        raise HTTPException(status_code=404, detail="Command or answer not found")
    
    answer_text = command.grounded_answer.answer_text
    lang = Language(request.target_language)
    
    # 1. Translate
    translated_text = await container.translator.translate(
        text=answer_text,
        target_language=lang
    )
    
    translation = Translation(
        answer_id=command.grounded_answer.id,
        target_language=lang,
        translated_text=translated_text,
    )
    await container.conversation_repository.save_translation(translation)
    
    # 2. TTS - use requested voice_id or fallback to CAPTAIN_PRESET
    from domain.voice.entities import VoiceProfile as VP
    if request.voice_id:
        tts_voice = VP(
            name="user-selected",
            language=lang,
            voice_id=request.voice_id,
        )
    else:
        tts_voice = CAPTAIN_PRESET
    audio_bytes = await container.tts.synthesize(
        text=translated_text,
        voice_profile=tts_voice,
    )
    
    audio_id = uuid.uuid4()
    audio_dir = "/tmp/captain_audio"
    os.makedirs(audio_dir, exist_ok=True)
    audio_path = f"{audio_dir}/{audio_id}.wav"
    with open(audio_path, "wb") as f:
        f.write(audio_bytes)
        
    audio = AudioResponse.create(
        translation_id=translation.id,
        voice_profile=tts_voice,
        audio_path=audio_path,
    )
    audio.id = audio_id
    await container.conversation_repository.save_audio_response(audio)
    
    return {
        "status": "success",
        "translated_text": translated_text,
        "audio_url": f"/api/v1/audio/{audio.id}",
        "target_language": request.target_language,
    }
