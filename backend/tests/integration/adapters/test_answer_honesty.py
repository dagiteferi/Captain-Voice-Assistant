"""The assistant must answer exactly, or say it does not have the fact."""

import asyncio
import tempfile
from typing import Sequence
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from adapters.outbound.llm.fake_adapter import FakeLLMAdapter
from adapters.outbound.tts.fake_adapter import FakeTTSAdapter
from application.ports.llm_port import LLMPort
from config.di_container import DIContainer
from domain.knowledge.entities import Document
from domain.knowledge.value_objects import ChunkRef
from tests.fakes import HashingEmbedder

import main


class RefusingLLMAdapter(LLMPort):
    """Stands in for a model that reports the passages lack the fact."""

    async def generate(
        self,
        query: str,
        chunks: Sequence[ChunkRef],
        *,
        system_prompt: str | None = None,
    ) -> str:
        return "The documents do not contain that information."


async def _app_client(tmp_path, llm=None):
    container = DIContainer(
        db_url=f"sqlite+aiosqlite:///{tmp_path / f'{uuid4()}.db'}",
        chroma_dir=tempfile.mkdtemp(),
        audio_dir=str(tmp_path / "audio"),
        embedder=HashingEmbedder(),
    )
    await container.init_db()
    container.llm = llm or FakeLLMAdapter()
    container.tts = FakeTTSAdapter()
    container.orchestrator.llm_port = container.llm
    container.orchestrator.tts_port = container.tts
    main._container = container
    return container, AsyncClient(
        transport=ASGITransport(app=main.create_app()), base_url="http://test"
    )


async def _ask(client, question: str) -> dict:
    headers = {"X-User-Role": "captain"}
    submit = await client.post(
        "/api/v1/commands",
        json={"input_text": question, "target_language": "en"},
        headers=headers,
    )
    assert submit.status_code == 202
    command_id = submit.json()["command_id"]

    for _ in range(40):
        poll = await client.get(f"/api/v1/commands/{command_id}", headers=headers)
        assert poll.status_code == 200
        result = poll.json()
        if result["status"] != "pending":
            return result
        await asyncio.sleep(0.25)
    raise AssertionError("pipeline did not finish")


@pytest.mark.asyncio
async def test_unanswerable_question_is_reported_as_ungrounded(tmp_path) -> None:
    """A missing fact must not be answered with a different, unrelated one."""
    container, client = await _app_client(tmp_path, llm=RefusingLLMAdapter())
    await container.ingest_documents.ingest(
        Document(title="contact", source_path="seed/contact.txt"),
        "Dagmawi Teferi is an AI Engineer. Phone: +251 920362324.",
    )
    async with client:
        result = await _ask(client, "how old are you")
        assert result["status"] == "ungrounded"
        # The contact passage must not be handed back as if it were the answer.
        assert not result["answer_text"]
        assert not result["citations"]
    await container.close()


@pytest.mark.asyncio
async def test_greeting_is_answered_conversationally(tmp_path) -> None:
    container, client = await _app_client(tmp_path, llm=RefusingLLMAdapter())
    await container.ingest_documents.ingest(
        Document(title="contact", source_path="seed/contact.txt"),
        "Dagmawi Teferi is an AI Engineer. Phone: +251 920362324.",
    )
    async with client:
        result = await _ask(client, "hii")
        assert result["status"] == "grounded"
        assert "how are you" in result["answer_text"].lower()
        # A greeting states no facts, so it cites nothing.
        assert result["citations"] == []
        # It is still spoken like any other reply.
        assert result["audio_url"]

        how_are_you = await _ask(client, "how are you?")
        assert "i am fine" in how_are_you["answer_text"].lower()
    await container.close()


@pytest.mark.asyncio
async def test_answerable_question_still_answers_from_the_knowledge_base(tmp_path) -> None:
    container, client = await _app_client(tmp_path)
    await container.ingest_documents.ingest(
        Document(title="education", source_path="seed/education.txt"),
        "Dagmawi Teferi earned a Bachelor of Computer Science with GPA 3.94 out of 4.0.",
    )
    async with client:
        result = await _ask(client, "what is his GPA")
        assert result["status"] == "grounded"
        assert "3.94" in result["answer_text"]
        assert result["citations"]
    await container.close()
