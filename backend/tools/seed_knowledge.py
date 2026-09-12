"""Seed the knowledge base with Dagmawi Teferi's professional profile documents.

Usage (backend must already be running):
    python tools/seed_knowledge.py
"""

import sys

import httpx

from application.knowledge.seed_documents import SAMPLE_DOCUMENTS

BACKEND_URL = "http://localhost:8000"


def main() -> None:
    print(f"Seeding {len(SAMPLE_DOCUMENTS)} profile knowledge documents...")
    print(f"Backend URL: {BACKEND_URL}")

    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            f"{BACKEND_URL}/api/v1/knowledge/replace-sample",
            headers={
                "Content-Type": "application/json",
                "X-User-Role": "captain",
            },
        )

        if response.status_code == 201:
            data = response.json()
            print(f"\nSuccessfully ingested {data['ingested_count']} documents!")
            ids = data.get("document_ids", [])
            print(f"  Document IDs: {ids[:3]}... (and {max(len(ids) - 3, 0)} more)")
            return

        print(f"\nFailed with status {response.status_code}")
        print(f"  Response: {response.text}")
        sys.exit(1)


if __name__ == "__main__":
    main()
