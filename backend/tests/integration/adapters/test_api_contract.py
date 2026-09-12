import asyncio
import tempfile
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from adapters.outbound.llm.fake_adapter import FakeLLMAdapter
from adapters.outbound.tts.fake_adapter import FakeTTSAdapter
from config.di_container import DIContainer
from domain.knowledge.entities import Document
from tests.fakes import HashingEmbedder

import main


async def _app_client(tmp_path):
    chroma_dir = tempfile.mkdtemp()
    db_path = tmp_path / f"{uuid4()}.db"
    container = DIContainer(
        db_url=f"sqlite+aiosqlite:///{db_path}",
        chroma_dir=chroma_dir,
        audio_dir=str(tmp_path / "audio"),
        embedder=HashingEmbedder(),
    )
    await container.init_db()
    fake_llm = FakeLLMAdapter()
    fake_tts = FakeTTSAdapter()
    container.llm = fake_llm
    container.tts = fake_tts
    container.orchestrator.llm_port = fake_llm
    container.orchestrator.tts_port = fake_tts
    main._container = container
    app = main.create_app()
    return container, AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_health_is_public(tmp_path) -> None:
    container, client = await _app_client(tmp_path)
    async with client:
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["version"] == "0.1.0"
        assert "stack" in data
    await container.close()


@pytest.mark.asyncio
async def test_cors_preflight(tmp_path) -> None:
    container, client = await _app_client(tmp_path)
    async with client:
        resp = await client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.status_code == 200
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
    await container.close()


@pytest.mark.asyncio
async def test_guest_cannot_submit_commands(tmp_path) -> None:
    container, client = await _app_client(tmp_path)
    async with client:
        resp = await client.post(
            "/api/v1/commands",
            json={"input_text": "What heading?", "target_language": "en"},
            headers={"X-User-Role": "guest"},
        )
        assert resp.status_code == 403
    await container.close()


@pytest.mark.asyncio
async def test_submit_command_returns_202_then_grounded_result_and_audio(tmp_path) -> None:
    container, client = await _app_client(tmp_path)
    await container.ingest_documents.ingest(
        Document(title="nav", source_path="seed/nav.txt"),
        "The vessel maintains a standing heading of 270 true.",
    )
    headers = {"X-User-Role": "captain"}
    async with client:
        submit = await client.post(
            "/api/v1/commands",
            json={"input_text": "What is the standing heading?", "target_language": "en"},
            headers=headers,
        )
        assert submit.status_code == 202
        body = submit.json()
        assert body["status"] == "pending"
        command_id = body["command_id"]

        result = None
        for _ in range(40):
            poll = await client.get(f"/api/v1/commands/{command_id}", headers=headers)
            assert poll.status_code == 200
            result = poll.json()
            if result["status"] != "pending":
                break
            await asyncio.sleep(0.25)

        assert result is not None
        assert result["status"] == "grounded"
        assert result["answer_text"]
        assert result["citations"]
        assert result["audio_url"]
        assert result["audio_url"].startswith("/api/v1/audio/")
        assert result["target_language"] == "en"

        audio_id = result["audio_url"].rsplit("/", 1)[-1]
        audio = await client.get(f"/api/v1/audio/{audio_id}", headers=headers)
        assert audio.status_code == 200
        assert audio.headers["content-type"].startswith("audio/")
        assert audio.content[:4] == b"RIFF"

        missing = await client.get(f"/api/v1/audio/{uuid4()}", headers=headers)
        assert missing.status_code == 404
        assert missing.json() == {"detail": "Audio response not found"}
    await container.close()
