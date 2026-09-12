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


@router.get("")
async def list_recent_commands(
    x_user_role: str = Header(...),
    limit: int = 20,
):
    if x_user_role not in ("captain", "crew"):
        raise HTTPException(status_code=403, detail="Access denied")

    from main import get_container
    container = get_container()
    commands = await container.conversation_repository.list_recent_commands(limit=limit)
    items = [
        {
            "command_id": str(cmd.id),
            "input_text": cmd.input_text,
            "status": cmd.status.value,
            "created_at": cmd.created_at.isoformat(),
        }
        for cmd in commands
    ]
    return {"commands": items}


@router.get("/{command_id}")
async def get_command(
    command_id: str,
    x_user_role: str = Header(...),
) -> GetCommandResponse:
    if x_user_role not in ("captain", "crew"):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        cmd_uuid = UUID(command_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Command not found")

    from main import get_container

    container = get_container()
    repository = container.conversation_repository

    command = await repository.get_command(cmd_uuid)
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
            target_language = translation.target_language.code
            audio = await repository.get_audio_for_translation(translation.id)
            if audio:
                audio_url = f"/api/v1/audio/{audio.id}"

    completed_at = None
    if command.status.value != "pending":
        events = await repository.list_events(cmd_uuid)
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
    command_id: str,
    x_user_role: str = Header(...),
) -> TraceResponse:
    if x_user_role not in ("captain", "crew"):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        cmd_uuid = UUID(command_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Command not found")

    from main import get_container
    import json

    container = get_container()
    repository = container.conversation_repository

    command = await repository.get_command(cmd_uuid)
    if command is None:
        raise HTTPException(status_code=404, detail="Command not found")

    rows = await repository.list_events_with_ids(cmd_uuid)
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

    return TraceResponse(command_id=cmd_uuid, events=trace_events)


@router.get("/{command_id}/stream")
async def stream_command_trace(
    command_id: str,
    x_user_role: str = Header(...),
    since_event_id: UUID | None = Query(None, alias="since_event_id"),
):
    if x_user_role not in ("captain", "crew"):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        cmd_uuid = UUID(command_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Command not found")

    from main import get_container

    container = get_container()
    command = await container.conversation_repository.get_command(cmd_uuid)
    if command is None:
        raise HTTPException(status_code=404, detail="Command not found")

    from adapters.inbound.api.sse import stream_events

    return await stream_events(cmd_uuid, since_event_id=since_event_id)


class RetranslateRequest(BaseModel):
    target_language: str
    voice_id: str | None = None

@router.post("/{command_id}/retranslate")
async def retranslate_command(
    command_id: str,
    request: RetranslateRequest,
    x_user_role: str = Header(...),
):
    if x_user_role not in ("captain", "crew"):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        cmd_uuid = UUID(command_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Command not found")

    if x_user_role not in ("captain", "crew"):
        raise HTTPException(status_code=403, detail="Access denied")

    from pathlib import Path
    from uuid import uuid4

    from domain.conversation.value_objects import Language
    from domain.voice.entities import AudioResponse, Translation, VoiceProfile
    from main import get_container

    container = get_container()
    command = await container.conversation_repository.get_command(cmd_uuid)
    if command is None or not command.grounded_answer:
        raise HTTPException(status_code=404, detail="Command or answer not found")

    lang = Language(request.target_language)
    try:
        translated_text = await container.translator.translate(
            command.grounded_answer.answer_text,
            lang,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Translation failed: {exc}") from exc

    translation = Translation(
        answer_id=command.grounded_answer.id,
        target_language=lang,
        translated_text=translated_text,
    )
    await container.conversation_repository.save_translation(translation)

    conversation = await container.conversation_repository.get_conversation(command.conversation_id)
    if conversation is not None:
        conversation.target_language = lang
        await container.conversation_repository.save_conversation(conversation)

    audio_url = None
    try:
        tts_voice = VoiceProfile(
            name="user-selected" if request.voice_id else "default",
            language=lang,
            voice_id=request.voice_id,
        )
        audio_bytes = await container.tts.synthesize(translated_text, tts_voice)
        if audio_bytes:
            existing = await container.conversation_repository.get_audio_for_translation(translation.id)
            audio_id = existing.id if existing else uuid4()
            audio_dir = Path(container._audio_dir)
            audio_dir.mkdir(parents=True, exist_ok=True)
            audio_path = audio_dir / f"{audio_id}.mp3"
            audio_path.write_bytes(audio_bytes)
            audio = AudioResponse.create(
                translation_id=translation.id,
                voice_profile=tts_voice,
                audio_path=str(audio_path),
                duration_ms=max(int(len(audio_bytes) / 16000 * 1000), 1),
            )
            audio.id = audio_id
            await container.conversation_repository.save_audio_response(audio)
            audio_url = f"/api/v1/audio/{audio.id}"
    except Exception as exc:
        logger = __import__("logging").getLogger(__name__)
        logger.warning("Retranslate TTS failed: %s", exc)

    return {
        "status": "success",
        "translated_text": translated_text,
        "audio_url": audio_url,
        "target_language": request.target_language,
    }
