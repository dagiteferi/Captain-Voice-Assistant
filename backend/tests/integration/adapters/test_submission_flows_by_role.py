"""Full integration tests for knowledge submission flows by role."""

import tempfile

import pytest
from httpx import AsyncClient, ASGITransport

from config.di_container import DIContainer
from tests.fakes import HashingEmbedder

import main


@pytest.mark.asyncio
async def test_captain_submission_auto_indexes_immediately():
    """Captain submissions should auto-approve and be immediately searchable."""
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
        
        # Captain submits
        payload = {
            "submitted_by": "captain-1",
            "submitter_role": "captain",
            "raw_content": "Captain knowledge: vessel speed is optimal at 15 knots.",
        }
        resp = await client.post("/api/v1/knowledge/submissions", json=payload, headers=captain_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "approved"

        # Verify it's immediately searchable
        results = await container.vector_store.search("vessel speed knots", limit=5)
        assert len(results) >= 1


@pytest.mark.asyncio
async def test_crew_submission_pending_then_searchable_after_approval():
    """Crew submissions should go to pending, then become searchable after captain approves."""
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
        crew_headers = {"X-User-Role": "crew-1"}
        
        # Crew submits (using captain header for submission endpoint since it's open)
        payload = {
            "submitted_by": "crew-1",
            "submitter_role": "crew",
            "raw_content": "Crew knowledge: emergency procedures require immediate notification.",
        }
        resp = await client.post("/api/v1/knowledge/submissions", json=payload, headers=captain_headers)
        assert resp.status_code == 201
        data = resp.json()
        submission_id = data["submission_id"]
        assert data["status"] == "pending"

        # Should NOT be searchable yet
        results = await container.vector_store.search("emergency procedures", limit=5)
        found = any("emergency" in r.content.lower() for r in results)
        assert not found

        # Captain approves
        approve_payload = {"reviewed_by": "captain-1"}
        approve_resp = await client.post(
            f"/api/v1/knowledge/submissions/{submission_id}/approve",
            json=approve_payload,
            headers=captain_headers,
        )
        assert approve_resp.status_code == 200

        # Now should be searchable
        results = await container.vector_store.search("emergency procedures", limit=5)
        assert len(results) >= 1


@pytest.mark.asyncio
async def test_guest_submission_always_pending():
    """Guest submissions should never auto-approve even if all rules pass."""
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
        
        # Guest submits clean content (passes all rules but is still guest)
        payload = {
            "submitted_by": "guest-1",
            "submitter_role": "guest",
            "raw_content": "Guest knowledge: this is clean content with no issues whatsoever.",
        }
        resp = await client.post("/api/v1/knowledge/submissions", json=payload, headers=captain_headers)
        assert resp.status_code == 201
        data = resp.json()
        submission_id = data["submission_id"]
        assert data["status"] == "pending"  # guest always pending

        # Should NOT be searchable
        results = await container.vector_store.search("guest knowledge clean", limit=5)
        found = any("guest" in r.content.lower() for r in results)
        assert not found

        # After approval, becomes searchable
        approve_payload = {"reviewed_by": "captain-1"}
        approve_resp = await client.post(
            f"/api/v1/knowledge/submissions/{submission_id}/approve",
            json=approve_payload,
            headers=captain_headers,
        )
        assert approve_resp.status_code == 200

        # Now searchable
        results = await container.vector_store.search("guest knowledge clean", limit=5)
        assert len(results) >= 1
