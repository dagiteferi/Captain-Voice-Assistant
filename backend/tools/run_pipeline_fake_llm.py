import asyncio
import sys
import tempfile
from uuid import uuid4
from pathlib import Path

# Ensure repo root is on sys.path when run as a script
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adapters.outbound.llm.fake_adapter import FakeLLMAdapter
from config.di_container import DIContainer
from domain.knowledge.entities import Document
from domain.conversation.entities import Conversation, Command
from domain.conversation.value_objects import Language


async def main() -> None:
    with tempfile.TemporaryDirectory() as chroma_dir:
        # Use a file-backed SQLite DB in a temp file to persist events
        db_url = f"sqlite+aiosqlite:///{tempfile.mktemp(suffix='.db')}"
        container = DIContainer(db_url=db_url, chroma_dir=chroma_dir)

        # Initialize DB schema
        await container.init_db()

        # Swap in the fake LLM for fast deterministic runs
        fake_llm = FakeLLMAdapter()
        container.llm = fake_llm
        container.orchestrator.llm_port = fake_llm

        # Ingest a trusted document
        doc = Document(id=uuid4(), title="nav-log", source_path="seed/nav.txt")
        await container.ingest_documents.ingest(doc, "The vessel maintains a standing heading of 270 true.")

        # Create conversation and submit a command
        conversation = Conversation(captain_id="captain-1", target_language=Language("en"))
        await container.conversation_repository.save_conversation(conversation)

        command = conversation.submit_command("What is the vessel's heading?")
        await container.conversation_repository.save_command(command)

        # Execute pipeline synchronously for the test
        outcome = await container.orchestrator.execute(command)

        print("Pipeline outcome:")
        print(" status:", outcome.status)
        if outcome.grounded_answer:
            print(" answer_text:", outcome.grounded_answer.answer_text)
            print(" citations:", [str(c.chunk_id) for c in outcome.grounded_answer.citations])

        # Fetch persisted events
        events = await container.conversation_repository.list_events(command.id)
        print(f"Persisted events ({len(events)}):")
        for e in events:
            print(" -", type(e).__name__, getattr(e, 'occurred_at', None))


if __name__ == "__main__":
    asyncio.run(main())
