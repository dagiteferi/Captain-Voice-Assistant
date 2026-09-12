from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class SubmitterRole(StrEnum):
    CAPTAIN = "captain"
    CREW = "crew"
    GUEST = "guest"


class SubmissionStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    INDEXED = "indexed"


class RuleVerdict(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    NEEDS_REVIEW = "needs_review"


@dataclass(frozen=True)
class ChunkRef:
    chunk_id: UUID
    document_id: UUID
    content: str
    # Ranking score: the best of embedding and keyword match, with boosts.
    similarity_score: float = 0.0
    # Plain embedding cosine, for judging how alike two texts actually are.
    cosine_score: float = 0.0


@dataclass(frozen=True)
class RetrievalResult:
    query: str
    chunks: tuple[ChunkRef, ...]
    attempt: int = 1
    relevant: bool = True


@dataclass(frozen=True)
class RuleOutcome:
    rule_name: str
    verdict: RuleVerdict
    reason: str = ""


@dataclass(frozen=True)
class RuleContext:
    max_similarity: float = 0.0
