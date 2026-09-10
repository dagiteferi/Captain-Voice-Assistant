from dataclasses import dataclass
from uuid import UUID

from domain.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class KnowledgeSubmissionQueued(DomainEvent):
    submission_id: UUID


@dataclass(frozen=True, kw_only=True)
class KnowledgeSubmissionApproved(DomainEvent):
    submission_id: UUID


@dataclass(frozen=True, kw_only=True)
class KnowledgeSubmissionRejected(DomainEvent):
    submission_id: UUID
    reason: str = ""


@dataclass(frozen=True, kw_only=True)
class KnowledgeIndexed(DomainEvent):
    submission_id: UUID
    document_id: UUID
