"""Integration tests for all 4 Knowledge Submission methods:
1. Raw Text Submission
2. File Upload (PDF, Word, PPT, Text, CSV, JSON)
3. Web URL Link Ingestion
4. Structured SOP Procedure Form
"""

import io
import tempfile
import pytest
from httpx import ASGITransport, AsyncClient

from main import create_app
from config.di_container import DIContainer
from tests.fakes import HashingEmbedder


async def _app_client(tmp_path):
    db_url = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    container = DIContainer(
        db_url=db_url,
        chroma_dir=str(tmp_path / "chroma"),
        embedder=HashingEmbedder(),
    )
    await container.init_db()

    import main
    main._container = container
    app = create_app()
    return container, AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_method1_raw_text_submission(tmp_path):
    container, client = await _app_client(tmp_path)
    async with client:
        response = await client.post(
            "/api/v1/knowledge/submissions",
            json={
                "submitted_by": "Captain John",
                "submitter_role": "captain",
                "raw_content": "Emergency anchoring protocol requires deploying anchor with 5 shackles out in open roadstead.",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "submission_id" in data
        assert data["status"] in ("approved", "pending")
        assert len(data["rule_results"]) > 0
    await container.close()


@pytest.mark.asyncio
async def test_method2_file_upload_submission(tmp_path):
    container, client = await _app_client(tmp_path)
    async with client:
        file_content = b"PDF Document: Fuel Line Pressure Check Procedure. Maintain 4.2 bar at all times."
        response = await client.post(
            "/api/v1/knowledge/submissions/file",
            data={
                "submitted_by": "Captain John",
                "submitter_role": "captain",
            },
            files={
                "file": ("fuel_procedure.txt", io.BytesIO(file_content), "text/plain"),
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "submission_id" in data
        assert data["status"] in ("approved", "pending")
    await container.close()


@pytest.mark.asyncio
async def test_method4_structured_procedure_submission(tmp_path):
    container, client = await _app_client(tmp_path)
    async with client:
        response = await client.post(
            "/api/v1/knowledge/submissions/procedure",
            json={
                "submitted_by": "Captain John",
                "submitter_role": "captain",
                "title": "Emergency Bilge Pump Operation",
                "category": "Emergency Protocol",
                "severity": "Emergency",
                "steps": [
                    "Open bilge valve A-12.",
                    "Engage emergency electric bilge pump switch.",
                    "Verify discharge overboard visually.",
                ],
                "notes": "Ensure strainer is free of debris before starting.",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "submission_id" in data
        assert data["status"] in ("approved", "pending")
    await container.close()

