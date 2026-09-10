from uuid import uuid4

import pytest

from domain.conversation.entities import Command, Conversation, GroundedAnswer
from domain.conversation.value_objects import Citation, CommandStatus, Language
from domain.exceptions import InvalidCommandTransition, UngroundedAnswerError


def test_grounded_answer_requires_citations() -> None:
    with pytest.raises(UngroundedAnswerError):
        GroundedAnswer(command_id=uuid4(), answer_text="The heading is 270.", citations=[])


def test_grounded_answer_rejects_blank_text() -> None:
    with pytest.raises(UngroundedAnswerError):
        GroundedAnswer(
            command_id=uuid4(),
            answer_text="   ",
            citations=[Citation(chunk_id=uuid4())],
        )


def test_grounded_answer_accepts_citation() -> None:
    citation = Citation(chunk_id=uuid4(), snippet="heading 270")
    answer = GroundedAnswer(
        command_id=uuid4(),
        answer_text="Steer 270.",
        citations=[citation],
    )
    answer.validate()
    assert answer.citations == [citation]


def test_command_rejects_empty_text() -> None:
    with pytest.raises(ValueError):
        Command(conversation_id=uuid4(), input_text=" ")


def test_command_attaches_grounded_answer() -> None:
    command = Command(conversation_id=uuid4(), input_text="What is the heading?")
    answer = GroundedAnswer(
        command_id=command.id,
        answer_text="270 degrees.",
        citations=[Citation(chunk_id=uuid4())],
    )
    command.attach_grounded_answer(answer)
    assert command.status is CommandStatus.GROUNDED
    assert command.grounded_answer is answer


def test_command_rejects_answer_for_another_command() -> None:
    command = Command(conversation_id=uuid4(), input_text="What is the heading?")
    answer = GroundedAnswer(
        command_id=uuid4(),
        answer_text="270 degrees.",
        citations=[Citation(chunk_id=uuid4())],
    )
    with pytest.raises(ValueError):
        command.attach_grounded_answer(answer)


def test_cannot_ground_a_failed_command() -> None:
    command = Command(conversation_id=uuid4(), input_text="What is the heading?")
    command.mark_failed()
    answer = GroundedAnswer(
        command_id=command.id,
        answer_text="270 degrees.",
        citations=[Citation(chunk_id=uuid4())],
    )
    with pytest.raises(InvalidCommandTransition):
        command.attach_grounded_answer(answer)


def test_conversation_submit_command() -> None:
    conversation = Conversation(captain_id="captain-1", target_language=Language("EN"))
    command = conversation.submit_command("Report wind.")
    assert command.conversation_id == conversation.id
    assert conversation.commands == [command]
    assert conversation.target_language.code == "en"


def test_language_rejects_short_code() -> None:
    with pytest.raises(ValueError):
        Language("x")
