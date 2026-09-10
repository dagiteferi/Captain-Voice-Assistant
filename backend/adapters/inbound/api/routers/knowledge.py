"""Knowledge base API routes."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Header, status
from pydantic import BaseModel

from main import get_container

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class IngestDocumentItem(BaseModel):
    title: str
    content: str


class IngestDocumentsRequest(BaseModel):
    documents: list[IngestDocumentItem]


class IngestDocumentsResponse(BaseModel):
    ingested_count: int
    document_ids: list[UUID]


@router.post("/documents", status_code=status.HTTP_201_CREATED)
async def ingest_documents(
    request: IngestDocumentsRequest,
    x_user_role: str = Header(...),
) -> IngestDocumentsResponse:
    """Bulk-load initial KB documents."""
    if x_user_role != "captain":
        raise HTTPException(status_code=403, detail="Only captain can ingest documents")

    from domain.knowledge.entities import Document
    from uuid import uuid4

    container = get_container()
    ingest = container.ingest_documents

    document_ids = []
    for doc_item in request.documents:
        doc_id = uuid4()
        document = Document(
            id=doc_id,
            title=doc_item.title,
            source_path=f"ingested/{doc_id}",
        )
        chunks = await ingest.ingest(document, doc_item.content)
        document_ids.append(doc_id)

    return IngestDocumentsResponse(
        ingested_count=len(request.documents),
        document_ids=document_ids,
    )


# Knowledge submission routes will be added in step 7
class SubmitKnowledgeRequest(BaseModel):
    submitted_by: str
    submitter_role: str
    raw_content: str


class RuleResultItem(BaseModel):
    rule: str
    outcome: str
    similarity: float | None = None


class SubmitKnowledgeResponse(BaseModel):
    submission_id: UUID
    status: str
    rule_results: list[RuleResultItem]


@router.post("/submissions", status_code=status.HTTP_201_CREATED)
async def submit_knowledge(
    request: SubmitKnowledgeRequest,
) -> SubmitKnowledgeResponse:
    """Propose new information for the knowledge base."""
    # Placeholder: step 7 implements the full rule engine
    from uuid import uuid4

    submission_id = uuid4()
    return SubmitKnowledgeResponse(
        submission_id=submission_id,
        status="pending",
        rule_results=[],
    )


@router.get("/submissions")
async def list_submissions(
    status: str | None = None,
    x_user_role: str = Header(...),
):
    """Review queue for pending submissions."""
    if x_user_role != "captain":
        raise HTTPException(status_code=403, detail="Only captain can review submissions")

    # Placeholder: step 7 implements this
    return {"submissions": []}


@router.get("/submissions/{submission_id}")
async def get_submission(
    submission_id: UUID,
    x_user_role: str = Header(...),
):
    """Get a single submission."""
    # Placeholder: step 7 implements this
    raise HTTPException(status_code=404, detail="Submission not found")


@router.post("/submissions/{submission_id}/approve")
async def approve_submission(
    submission_id: UUID,
    x_user_role: str = Header(...),
):
    """Approve and index a submission."""
    if x_user_role != "captain":
        raise HTTPException(status_code=403, detail="Only captain can approve submissions")

    # Placeholder: step 7 implements this
    raise HTTPException(status_code=404, detail="Submission not found")


@router.post("/submissions/{submission_id}/reject")
async def reject_submission(
    submission_id: UUID,
    x_user_role: str = Header(...),
):
    """Reject a submission."""
    if x_user_role != "captain":
        raise HTTPException(status_code=403, detail="Only captain can reject submissions")

    # Placeholder: step 7 implements this
    raise HTTPException(status_code=404, detail="Submission not found")
