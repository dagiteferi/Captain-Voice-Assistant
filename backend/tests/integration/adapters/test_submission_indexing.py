"""Tests for knowledge submission indexing."""

import tempfile
from uuid import uuid4

import pytest
from httpx import AsyncClient, ASGITransport

from config.di_container import DIContainer
from tests.fakes import HashingEmbedder
from domain.knowledge.entities import KnowledgeSubmission
from domain.knowledge.value_objects import SubmitterRole, SubmissionStatus

import main


@pytest.mark.asyncio
async def test_approved_submission_is_searchable():
    """Verify that approving a submission indexes it into the vector store and makes it searchable."""
    chroma_dir = tempfile.mkdtemp()
    db_path = tempfile.mktemp(suffix=".db")
    db_url = f"sqlite+aiosqlite:///{db_path}"

    container = DIContainer(db_url=db_url, chroma_dir=chroma_dir, embedder=HashingEmbedder())
    await container.init_db()

    main._container = container

    app = main.create_app()
    transport = ASGITransport(app=app)
    
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        captain_headers = {"X-User-Role": "captain"}
        
        # Submit crew content (goes to pending)
        crew_payload = {
            "submitted_by": "crew-1",
            "submitter_role": "crew",
            "raw_content": "The vessel heading should be 180 degrees magnetic south.",
        }
        submit_resp = await client.post(
            "/api/v1/knowledge/submissions", json=crew_payload, headers=captain_headers
        )
        assert submit_resp.status_code == 201
        sub_data = submit_resp.json()
        submission_id = sub_data["submission_id"]

        # Approve the submission
        approve_payload = {"reviewed_by": "captain-1"}
        approve_resp = await client.post(
            f"/api/v1/knowledge/submissions/{submission_id}/approve",
            json=approve_payload,
            headers=captain_headers,
        )
        assert approve_resp.status_code == 200

        # Verify it's now indexed by searching for the content
        results = await container.vector_store.search("heading magnetic south", limit=5)
        assert len(results) >= 1
        assert "heading" in results[0].content.lower()
