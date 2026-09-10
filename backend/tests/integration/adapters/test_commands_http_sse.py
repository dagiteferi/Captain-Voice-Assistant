import asyncio
import json
import tempfile
from uuid import uuid4

import pytest
from datetime import datetime
from httpx import AsyncClient, ASGITransport

from config.di_container import DIContainer
from adapters.outbound.llm.fake_adapter import FakeLLMAdapter
from adapters.outbound.tts.fake_adapter import FakeTTSAdapter
from tests.fakes import HashingEmbedder
from domain.knowledge.entities import Document
from domain.conversation.entities import Conversation
from domain.conversation.value_objects import Language

import main


@pytest.mark.asyncio
async def test_trace_and_command_status():
    chroma_dir = tempfile.mkdtemp()
    db_path = tempfile.mktemp(suffix=".db")
    db_url = f"sqlite+aiosqlite:///{db_path}"

    container = DIContainer(db_url=db_url, chroma_dir=chroma_dir, embedder=HashingEmbedder())
    await container.init_db()

    fake = FakeLLMAdapter()
    fake_tts = FakeTTSAdapter()
    container.llm = fake
    container.tts = fake_tts
    container.orchestrator.llm_port = fake
    container.orchestrator.tts_port = fake_tts

    main._container = container

    # ingest a doc
    doc = Document(id=uuid4(), title="nav", source_path="seed/nav.txt")
    await container.ingest_documents.ingest(doc, "The vessel maintains a standing heading of 270 true.")

    # create conversation and command
    conversation = Conversation(captain_id="captain-1", target_language=Language("en"))
    await container.conversation_repository.save_conversation(conversation)
    command = conversation.submit_command("What heading?")
    await container.conversation_repository.save_command(command)

    app = main.create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # run orchestrator in background
        task = asyncio.create_task(container.orchestrator.execute(command))
        await task

        headers = {"X-User-Role": "captain"}
        trace_resp = await client.get(f"/api/v1/commands/{command.id}/trace", headers=headers)
        assert trace_resp.status_code == 200
        trace_json = trace_resp.json()
        assert trace_json.get("command_id")
        events = trace_json.get("events", [])
        prev_dt = None
        for ev in events:
            assert "event_type" in ev and "payload" in ev and "occurred_at" in ev
            dt = datetime.fromisoformat(ev["occurred_at"])
            if prev_dt is not None:
                assert dt >= prev_dt
            prev_dt = dt

        # GET command status
        cmd_resp = await client.get(f"/api/v1/commands/{command.id}", headers=headers)
        assert cmd_resp.status_code == 200
        cmd_json = cmd_resp.json()
        assert cmd_json.get("status") in ("grounded", "ungrounded", "failed", "pending")


@pytest.mark.asyncio
async def test_sse_stream_order_and_payload():
    chroma_dir = tempfile.mkdtemp()
    db_path = tempfile.mktemp(suffix=".db")
    db_url = f"sqlite+aiosqlite:///{db_path}"

    container = DIContainer(db_url=db_url, chroma_dir=chroma_dir, embedder=HashingEmbedder())
    await container.init_db()

    fake = FakeLLMAdapter()
    fake_tts = FakeTTSAdapter()
    container.llm = fake
    container.tts = fake_tts
    container.orchestrator.llm_port = fake
    container.orchestrator.tts_port = fake_tts

    main._container = container

    # ingest a doc
    doc = Document(id=uuid4(), title="nav", source_path="seed/nav.txt")
    await container.ingest_documents.ingest(doc, "The vessel maintains a standing heading of 270 true.")

    # create conversation and command
    conversation = Conversation(captain_id="captain-1", target_language=Language("en"))
    await container.conversation_repository.save_conversation(conversation)
    command = conversation.submit_command("Report heading again.")
    await container.conversation_repository.save_command(command)

    app = main.create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # start orchestration but don't await
        bg = asyncio.create_task(container.orchestrator.execute(command))

        headers = {"X-User-Role": "captain"}
        stream_url = f"/api/v1/commands/{command.id}/stream"
        async with client.stream("GET", stream_url, headers=headers, timeout=30.0) as response:
            assert response.status_code == 200
            received = []
            async for raw in response.aiter_lines():
                if not raw:
                    continue
                if raw.startswith("data: "):
                    payload = raw[len("data: "):]
                    try:
                        obj = json.loads(payload)
                        received.append(obj)
                        assert "event_type" in obj and "occurred_at" in obj and "payload" in obj
                        # stop on terminal events
                        if obj["event_type"] in ("AudioSynthesized", "AudioResponseReady", "PipelineFallback"):
                            break
                    except Exception:
                        pass

        await bg
        assert len(received) >= 1