"""Value objects used within the conversation domain."""

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class Citation:
    source: str
    page: int | None = None
    snippet: str | None = None


@dataclass(frozen=True)
class Language:
    code: str


class PipelineStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
