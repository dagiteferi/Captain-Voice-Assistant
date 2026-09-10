"""Port for knowledge submission persistence."""

from abc import ABC, abstractmethod
from uuid import UUID

from domain.knowledge.entities import KnowledgeSubmission


class KnowledgeSubmissionRepositoryPort(ABC):
    @abstractmethod
    async def save_submission(self, submission: KnowledgeSubmission) -> None:
        """Save or update a knowledge submission."""
        pass

    @abstractmethod
    async def get_submission(self, submission_id: UUID) -> KnowledgeSubmission | None:
        """Get a submission by ID."""
        pass

    @abstractmethod
    async def list_submissions(self, status: str | None = None) -> list[KnowledgeSubmission]:
        """List submissions, optionally filtered by status."""
        pass
