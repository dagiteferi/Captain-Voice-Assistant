from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from domain.conversation.value_objects import (
    Citation,
    CommandStatus,
    Language,
    PipelineStatus,
)
from domain.exceptions import InvalidCommandTransition, UngroundedAnswerError


@dataclass
class GroundedAnswer:
    command_id: UUID
    answer_text: str
    citations: list[Citation]
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not self.answer_text.strip():
            raise UngroundedAnswerError("answer text is empty")
        if not self.citations:
            raise UngroundedAnswerError("a grounded answer must cite at least one chunk")


@dataclass
class Command:
    conversation_id: UUID
    input_text: str
    id: UUID = field(default_factory=uuid4)
    status: CommandStatus = CommandStatus.PENDING
    grounded_answer: GroundedAnswer | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.input_text.strip():
            raise ValueError("command text is empty")

    def attach_grounded_answer(self, answer: GroundedAnswer) -> None:
        if self.status not in {CommandStatus.PENDING, CommandStatus.UNGROUNDED}:
            raise InvalidCommandTransition(
                f"cannot ground a command in status {self.status}"
            )
        if answer.command_id != self.id:
            raise ValueError("answer does not belong to this command")
        answer.validate()
        self.grounded_answer = answer
        self.status = CommandStatus.GROUNDED

    def mark_ungrounded(self) -> None:
        if self.status == CommandStatus.FAILED:
            raise InvalidCommandTransition("cannot mark a failed command as ungrounded")
        self.grounded_answer = None
        self.status = CommandStatus.UNGROUNDED

    def mark_failed(self) -> None:
        self.status = CommandStatus.FAILED


@dataclass
class Conversation:
    captain_id: str
    target_language: Language
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    commands: list[Command] = field(default_factory=list)

    def submit_command(self, input_text: str) -> Command:
        command = Command(conversation_id=self.id, input_text=input_text)
        self.commands.append(command)
        return command


@dataclass
class PipelineTrace:
    command_id: UUID
    status: PipelineStatus
    events: list[object] = field(default_factory=list)
