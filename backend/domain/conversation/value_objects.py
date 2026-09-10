from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class CommandStatus(StrEnum):
    PENDING = "pending"
    GROUNDED = "grounded"
    UNGROUNDED = "ungrounded"
    FAILED = "failed"


class PipelineStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    GROUNDED = "grounded"
    UNGROUNDED = "ungrounded"
    FAILED = "failed"


@dataclass(frozen=True)
class Language:
    code: str

    def __post_init__(self) -> None:
        normalized = self.code.strip().lower()
        if len(normalized) < 2:
            raise ValueError("language code must be at least two characters")
        object.__setattr__(self, "code", normalized)


@dataclass(frozen=True)
class Citation:
    chunk_id: UUID
    document_id: UUID | None = None
    snippet: str | None = None
