from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/audio", tags=["audio"])


@router.get("/{audio_response_id}")
async def get_audio(
    audio_response_id: UUID,
    x_user_role: str | None = Header(None),
) -> FileResponse:
    if x_user_role and x_user_role not in ("captain", "crew"):
        raise HTTPException(status_code=403, detail="Access denied")

    from main import get_container

    container = get_container()
    audio = await container.conversation_repository.get_audio_response(audio_response_id)
    if audio is None:
        raise HTTPException(status_code=404, detail="Audio response not found")

    path = Path(audio.audio_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Audio response not found")

    media_type = "audio/wav" if path.suffix.lower() == ".wav" else "audio/mpeg"
    return FileResponse(path, media_type=media_type, filename=path.name)
