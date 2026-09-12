"""Integration tests for knowledge submission repository."""

import json
import tempfile
from uuid import uuid4

import pytest

from config.di_container import DIContainer
from domain.knowledge.entities import KnowledgeSubmission
from domain.knowledge.value_objects import SubmitterRole, SubmissionStatus


@pytest.mark.asyncio
async def test_save_and_get_submission():
    db_path = tempfile.mktemp(suffix=".db")
    db_url = f"sqlite+aiosqlite:///{db_path}"

    container = DIContainer(db_url=db_url, chroma_dir=tempfile.mkdtemp())
    await container.init_db()

    repository = container.conversation_repository

    # Create and save a submission
    sub = KnowledgeSubmission(
        submitted_by="crew-1",
        submitter_role=SubmitterRole.CREW,
        raw_content="This is a test knowledge submission with at least 20 chars.",
    )
    sub.record_rule_results([{"rule": "MinMaxLengthRule", "outcome": "pass"}])

    await repository.save_submission(sub)

    # Retrieve and verify
    retrieved = await repository.get_submission(sub.id)
    assert retrieved is not None
    assert retrieved.id == sub.id
    assert retrieved.submitted_by == "crew-1"
    assert retrieved.status == SubmissionStatus.PENDING


@pytest.mark.asyncio
async def test_list_submissions_with_status_filter():
    db_path = tempfile.mktemp(suffix=".db")
    db_url = f"sqlite+aiosqlite:///{db_path}"

    container = DIContainer(db_url=db_url, chroma_dir=tempfile.mkdtemp())
    await container.init_db()

    repository = container.conversation_repository

    # Create submissions with different statuses
    sub1 = KnowledgeSubmission(
        submitted_by="captain-1",
        submitter_role=SubmitterRole.CAPTAIN,
        raw_content="Content 1 that meets minimum length requirements for submission.",
        status=SubmissionStatus.APPROVED,
    )

    sub2 = KnowledgeSubmission(
        submitted_by="crew-1",
        submitter_role=SubmitterRole.CREW,
        raw_content="Content 2 that meets minimum length requirements for submission.",
        status=SubmissionStatus.PENDING,
    )

    await repository.save_submission(sub1)
    await repository.save_submission(sub2)

    # Filter by status
    pending = await repository.list_submissions(status=SubmissionStatus.PENDING.value)
    assert len(pending) == 1
    assert pending[0].submitted_by == "crew-1"

    approved = await repository.list_submissions(status=SubmissionStatus.APPROVED.value)
    assert len(approved) == 1
    assert approved[0].submitted_by == "captain-1"


@pytest.mark.asyncio
async def test_save_submission_updates_raw_content():
    db_path = tempfile.mktemp(suffix=".db")
    db_url = f"sqlite+aiosqlite:///{db_path}"

    container = DIContainer(db_url=db_url, chroma_dir=tempfile.mkdtemp())
    await container.init_db()
    repository = container.conversation_repository

    sub = KnowledgeSubmission(
        submitted_by="captain-1",
        submitter_role=SubmitterRole.CAPTAIN,
        raw_content="Original knowledge text that is long enough to save.",
        status=SubmissionStatus.APPROVED,
    )
    await repository.save_submission(sub)
    sub.raw_content = "I was born in 1999 at Adama. This is the updated knowledge fact."
    await repository.save_submission(sub)

    loaded = await repository.get_submission(sub.id)
    assert loaded is not None
    assert "1999" in loaded.raw_content
    assert "Adama" in loaded.raw_content
