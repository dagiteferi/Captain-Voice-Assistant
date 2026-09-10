from dataclasses import dataclass
from uuid import UUID

from domain.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class RetrievalCompleted(DomainEvent):
    command_id: UUID
    query: str
    chunk_ids: tuple[UUID, ...]
    similarity_scores: tuple[float, ...]
    relevant: bool


@dataclass(frozen=True, kw_only=True)
class AnswerGrounded(DomainEvent):
    command_id: UUID
    answer_id: UUID
    citations: tuple


@dataclass(frozen=True, kw_only=True)
class PipelineFallback(DomainEvent):
    command_id: UUID
    reason: str


@dataclass(frozen=True, kw_only=True)
class AudioResponseReady(DomainEvent):
    command_id: UUID
    audio_response_id: UUID
