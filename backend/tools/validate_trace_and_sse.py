import asyncio
import sys
from pathlib import Path
import tempfile
from uuid import uuid4
import json
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import httpx
from httpx import ASGITransport

from config.di_container import DIContainer
from adapters.outbound.llm.fake_adapter import FakeLLMAdapter
from domain.knowledge.entities import Document
from domain.conversation.entities import Conversation, Command
from domain.conversation.value_objects import Language
import main


async def run_validation():
    chroma_dir = tempfile.mkdtemp()
    db_path = tempfile.mktemp(suffix=".db")
    db_url = f"sqlite+aiosqlite:///{db_path}"

    container = DIContainer(db_url=db_url, chroma_dir=chroma_dir)
    # initialize schema
    await container.init_db()

    # swap in fake llm
    fake = FakeLLMAdapter()
    container.llm = fake
    container.orchestrator.llm_port = fake

    # install container into main so routers use it
    main._container = container

    # ingest a doc
    doc = Document(id=uuid4(), title="nav", source_path="seed/nav.txt")
    await container.ingest_documents.ingest(doc, "The vessel maintains a standing heading of 270 true.")

    # create conversation+command
    conversation = Conversation(captain_id="captain-1", target_language=Language("en"))
    await container.conversation_repository.save_conversation(conversation)
    command = conversation.submit_command("What heading?")
    await container.conversation_repository.save_command(command)

    app = main.create_app()

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Start orchestration in background
        task = asyncio.create_task(container.orchestrator.execute(command))

        # Wait for pipeline to finish
        await task

        # 1) GET /commands/{id}/trace
        headers = {"X-User-Role": "captain"}
        trace_resp = await client.get(f"/api/v1/commands/{command.id}/trace", headers=headers)
        print("TRACE status", trace_resp.status_code)
        trace_json = trace_resp.json()
        print("TRACE body:", json.dumps(trace_json, indent=2))

        # Validate shape and occurred_at ISO
        events = trace_json.get("events", [])
        assert "command_id" in trace_json
        prev_dt = None
        for ev in events:
            assert "event_type" in ev and "payload" in ev and "occurred_at" in ev
            # ISO parse
            dt = datetime.fromisoformat(ev["occurred_at"])
            if prev_dt is not None:
                assert dt >= prev_dt, "events not in ascending order"
            prev_dt = dt

        # 2) GET /commands/{id}
        cmd_resp = await client.get(f"/api/v1/commands/{command.id}", headers=headers)
        print("COMMAND status", cmd_resp.status_code)
        cmd_json = cmd_resp.json()
        print("COMMAND body:", json.dumps(cmd_json, indent=2))
        assert cmd_json.get("status") in ("grounded", "ungrounded", "failed", "pending")

        # 3) SSE test: run another command and stream while it runs
        # create a second command
        command2 = conversation.submit_command("Report heading again.")
        await container.conversation_repository.save_command(command2)

        # start orchestration but do not await
        bg = asyncio.create_task(container.orchestrator.execute(command2))

        # stream SSE
        stream_url = f"/api/v1/commands/{command2.id}/stream"
        async with client.stream("GET", stream_url, headers=headers, timeout=30.0) as response:
            print("SSE status", response.status_code)
            received = []
            async for raw in response.aiter_lines():
                if not raw:
                    continue
                # SSE messages come with 'event: ...' or 'data: ...'
                if raw.startswith("data: "):
                    payload = raw[len("data: "):]
                    try:
                        obj = json.loads(payload)
                        print("SSE event:", obj)
                        # Validate fields
                        assert "event_type" in obj and "occurred_at" in obj
                        datetime.fromisoformat(obj["occurred_at"])  # parse
                        received.append(obj)
                        # stop when terminal event seen
                        if obj["event_type"] in ("AudioSynthesized", "AudioResponseReady", "PipelineFallback"):
                            break
                    except Exception as e:
                        print("SSE parse error:", e)
                # stop guard
                if len(received) >= 10:
                    break

        await bg

    print("Validation complete")


if __name__ == "__main__":
    asyncio.run(run_validation())
