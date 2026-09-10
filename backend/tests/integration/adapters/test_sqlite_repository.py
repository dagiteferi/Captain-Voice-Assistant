from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from sqlalchemy import text

from adapters.outbound.persistence.migrations import (
    create_session_factory,
    create_sqlite_engine,
    run_migrations,
)
from adapters.outbound.persistence.models import Base
from adapters.outbound.persistence.sqlite_repository import SQLiteConversationRepository
from domain.conversation.entities import Command, Conversation, GroundedAnswer
from domain.conversation.events import RetrievalCompleted
from domain.conversation.value_objects import Citation, CommandStatus, Language
from domain.voice.entities import CAPTAIN_PRESET, AudioResponse, Translation
from domain.voice.events import TranslationCompleted


@pytest.fixture
async def repo(tmp_path) -> AsyncIterator[SQLiteConversationRepository]:
    engine = create_sqlite_engine(f"sqlite+aiosqlite:///{tmp_path / 'captain.db'}")
    await run_migrations(engine)
    try:
        yield SQLiteConversationRepository(create_session_factory(engine))
    finally:
        await engine.dispose()


async def test_migrations_create_schema_tables(tmp_path) -> None:
    engine = create_sqlite_engine(f"sqlite+aiosqlite:///{tmp_path / 'schema.db'}")
    await run_migrations(engine)
    async with engine.connect() as connection:
        names = set(
            (await connection.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))).scalars().all()
        )
    await engine.dispose()
    expected = set(Base.metadata.tables)
    assert expected <= names


async def test_save_and_load_conversation_with_grounded_command(
    repo: SQLiteConversationRepository,
) -> None:
    conversation = Conversation(captain_id="captain-1", target_language=Language("en"))
    command = conversation.submit_command("What is the standing heading?")
    answer = GroundedAnswer(
        command_id=command.id,
        answer_text="Two seven zero true.",
        citations=[Citation(chunk_id=uuid4(), snippet="heading 270")],
    )
    command.attach_grounded_answer(answer)

    await repo.save_conversation(conversation)
    await repo.save_command(command)
    await repo.save_grounded_answer(answer)

    loaded = await repo.get_conversation(conversation.id)
    assert loaded is not None
    assert loaded.captain_id == "captain-1"
    assert loaded.commands[0].status is CommandStatus.GROUNDED
    assert loaded.commands[0].grounded_answer is not None
    assert loaded.commands[0].grounded_answer.answer_text == "Two seven zero true."
    assert loaded.commands[0].grounded_answer.citations[0].snippet == "heading 270"


async def test_translation_audio_and_event_roundtrip(
    repo: SQLiteConversationRepository,
) -> None:
    conversation = Conversation(captain_id="captain-1", target_language=Language("am"))
    command = conversation.submit_command("Report heading.")
    answer = GroundedAnswer(
        command_id=command.id,
        answer_text="Heading is 270.",
        citations=[Citation(chunk_id=uuid4())],
    )
    command.attach_grounded_answer(answer)
    translation = Translation(
        answer_id=answer.id,
        target_language=Language("am"),
        translated_text="አቅጣጫው 270 ነው።",
    )
    audio = AudioResponse.create(
        translation_id=translation.id,
        voice_profile=CAPTAIN_PRESET,
        audio_path="/tmp/captain.wav",
        duration_ms=800,
    )

    await repo.save_conversation(conversation)
    await repo.save_command(command)
    await repo.save_grounded_answer(answer)
    await repo.save_translation(translation)
    await repo.save_audio_response(audio)
    await repo.append_event(
        command.id,
        RetrievalCompleted(
            command_id=command.id,
            query=command.input_text,
            chunk_ids=(uuid4(),),
            relevant=True,
        ),
    )
    await repo.append_event(
        command.id,
        TranslationCompleted(
            command_id=command.id,
            translation_id=translation.id,
            target_language=Language("am"),
        ),
    )

    events = await repo.list_events(command.id)
    assert len(events) == 2
    assert isinstance(events[0], RetrievalCompleted)
    assert events[0].relevant is True
    assert isinstance(events[1], TranslationCompleted)
    assert events[1].target_language.code == "am"

    loaded_command = await repo.get_command(command.id)
    assert loaded_command is not None
    assert loaded_command.grounded_answer is not None
