from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from domain.exceptions import InvalidSubmissionTransition
from domain.knowledge.value_objects import SubmissionStatus, SubmitterRole


@dataclass(frozen=True)
class Document:
    title: str
    source_path: str
    id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class Chunk:
    document_id: UUID
    content: str
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError("chunk content is empty")


@dataclass
class KnowledgeSubmission:
    submitted_by: str
    submitter_role: SubmitterRole
    raw_content: str
    id: UUID = field(default_factory=uuid4)
    status: SubmissionStatus = SubmissionStatus.PENDING
    rule_results: list[dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    reviewed_by: str | None = None

    def __post_init__(self) -> None:
        if not self.raw_content.strip():
            raise ValueError("submission content is empty")
        if not self.submitted_by.strip():
            raise ValueError("submitted_by is required")

    def record_rule_results(self, results: list[dict]) -> None:
        self.rule_results = list(results)

    def approve(self, reviewed_by: str | None = None) -> None:
        if self.status in {SubmissionStatus.REJECTED, SubmissionStatus.INDEXED}:
            raise InvalidSubmissionTransition(
                f"cannot approve a submission in status {self.status}"
            )
        self.status = SubmissionStatus.APPROVED
        if reviewed_by:
            self.reviewed_by = reviewed_by

    def reject(self, reviewed_by: str | None = None) -> None:
        if self.status == SubmissionStatus.INDEXED:
            raise InvalidSubmissionTransition("cannot reject an already indexed submission")
        self.status = SubmissionStatus.REJECTED
        if reviewed_by:
            self.reviewed_by = reviewed_by

    def mark_indexed(self) -> None:
        if self.status != SubmissionStatus.APPROVED:
            raise InvalidSubmissionTransition("only an approved submission can be indexed")
        self.status = SubmissionStatus.INDEXED
