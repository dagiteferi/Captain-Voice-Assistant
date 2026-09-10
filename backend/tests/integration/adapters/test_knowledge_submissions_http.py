"""HTTP tests for knowledge submission endpoints."""

import json
import tempfile
from uuid import uuid4

import pytest
from httpx import AsyncClient, ASGITransport

from config.di_container import DIContainer
from tests.fakes import HashingEmbedder

import main


@pytest.mark.asyncio
async def test_submit_knowledge_endpoint():
    chroma_dir = tempfile.mkdtemp()
    db_path = tempfile.mktemp(suffix=".db")
    db_url = f"sqlite+aiosqlite:///{db_path}"

    container = DIContainer(db_url=db_url, chroma_dir=chroma_dir, embedder=HashingEmbedder())
    await container.init_db()

    main._container = container

    app = main.create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"X-User-Role": "captain"}
        payload = {
            "submitted_by": "captain-1",
            "submitter_role": "captain",
            "raw_content": "This is a well-formed knowledge submission with enough characters.",
        }
        resp = await client.post("/api/v1/knowledge/submissions", json=payload, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert "submission_id" in data
        assert data["status"] == "approved"  # captain auto-approves
        assert len(data["rule_results"]) == 4


@pytest.mark.asyncio
async def test_list_submissions_endpoint():
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
        
        # Submit a crew submission (goes to pending)
        crew_payload = {
            "submitted_by": "crew-1",
            "submitter_role": "crew",
            "raw_content": "This is crew knowledge that requires review before indexing.",
        }
        submit_resp = await client.post(
            "/api/v1/knowledge/submissions", json=crew_payload, headers=captain_headers
        )
        assert submit_resp.status_code == 201
        sub_data = submit_resp.json()
        assert sub_data["status"] == "pending"  # crew -> pending

        # List pending submissions
        list_resp = await client.get(
            "/api/v1/knowledge/submissions?status=pending", headers=captain_headers
        )
        assert list_resp.status_code == 200
        submissions = list_resp.json()["submissions"]
        assert len(submissions) >= 1
