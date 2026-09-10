"""Knowledge base API routes."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Header, status
from pydantic import BaseModel

# Import `get_container` lazily inside handlers to avoid import-time circular imports

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

    from main import get_container
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
    from main import get_container
    from domain.knowledge.entities import KnowledgeSubmission, Document, Chunk
    from domain.knowledge.value_objects import SubmitterRole
    from domain.knowledge.rules import evaluate_submission
    from uuid import uuid4

    container = get_container()
    repository = container.conversation_repository

    submitter_role = SubmitterRole(request.submitter_role)
    submission = KnowledgeSubmission(
        submitted_by=request.submitted_by,
        submitter_role=submitter_role,
        raw_content=request.raw_content,
    )

    hits = await container.vector_store.search(request.raw_content, limit=1)
    max_similarity = hits[0].similarity_score if hits else 0.0
    status_result, rule_results = evaluate_submission(
        submission,
        submitter_role,
        similarity_fn=lambda _: max_similarity,
    )
    submission.status = status_result
    submission.record_rule_results(rule_results)

    if status_result.value == "approved":
        doc = Document(
            id=uuid4(),
            title=f"Submission {submission.id}",
            source_path=f"submissions/{submission.id}",
        )
        chunk = Chunk(document_id=doc.id, content=submission.raw_content)
        await container.vector_store.upsert(chunk)
        submission.mark_indexed()

    await repository.save_submission(submission)

    return SubmitKnowledgeResponse(
        submission_id=submission.id,
        status=status_result.value,
        rule_results=[RuleResultItem(**r) for r in rule_results],
    )


class SubmissionItem(BaseModel):
    id: UUID
    submitted_by: str
    submitter_role: str
    raw_content: str
    status: str
    created_at: str


class ListSubmissionsResponse(BaseModel):
    submissions: list[SubmissionItem]


@router.get("/submissions")
async def list_submissions(
    status: str | None = None,
    x_user_role: str = Header(...),
) -> ListSubmissionsResponse:
    """Review queue for pending submissions."""
    if x_user_role != "captain":
        raise HTTPException(status_code=403, detail="Only captain can review submissions")

    from main import get_container

    container = get_container()
    repository = container.conversation_repository

    submissions = await repository.list_submissions(status=status)
    items = [
        SubmissionItem(
            id=s.id,
            submitted_by=s.submitted_by,
            submitter_role=s.submitter_role.value,
            raw_content=s.raw_content,
            status=s.status.value,
            created_at=s.created_at.isoformat(),
        )
        for s in submissions
    ]
    return ListSubmissionsResponse(submissions=items)


class SubmissionDetailResponse(BaseModel):
    id: UUID
    submitted_by: str
    submitter_role: str
    raw_content: str
    status: str
    rule_results: list[RuleResultItem]
    reviewed_by: str | None = None
    created_at: str


@router.get("/submissions/{submission_id}")
async def get_submission(
    submission_id: UUID,
    x_user_role: str = Header(...),
) -> SubmissionDetailResponse:
    """Get a single submission."""
    from main import get_container

    container = get_container()
    repository = container.conversation_repository

    submission = await repository.get_submission(submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Crew/guest can only access their own
    if x_user_role != "captain" and submission.submitted_by != x_user_role:
        raise HTTPException(status_code=403, detail="Access denied")

    rule_results = submission.rule_results if isinstance(submission.rule_results, list) else []
    return SubmissionDetailResponse(
        id=submission.id,
        submitted_by=submission.submitted_by,
        submitter_role=submission.submitter_role.value,
        raw_content=submission.raw_content,
        status=submission.status.value,
        rule_results=[RuleResultItem(**r) for r in rule_results],
        reviewed_by=submission.reviewed_by,
        created_at=submission.created_at.isoformat(),
    )


class ApproveSubmissionRequest(BaseModel):
    reviewed_by: str


class ApproveSubmissionResponse(BaseModel):
    id: UUID
    status: str
    indexed: bool


@router.post("/submissions/{submission_id}/approve")
async def approve_submission(
    submission_id: UUID,
    request: ApproveSubmissionRequest,
    x_user_role: str = Header(...),
) -> ApproveSubmissionResponse:
    """Approve and index a submission."""
    if x_user_role != "captain":
        raise HTTPException(status_code=403, detail="Only captain can approve submissions")

    from main import get_container
    from domain.knowledge.entities import Document, Chunk
    from uuid import uuid4

    container = get_container()
    repository = container.conversation_repository

    submission = await repository.get_submission(submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    submission.approve(reviewed_by=request.reviewed_by)

    indexed = False
    try:
        doc = Document(id=uuid4(), title=f"Submission {submission_id}", source_path=f"submissions/{submission_id}")
        chunk = Chunk(document_id=doc.id, content=submission.raw_content)
        await container.vector_store.upsert(chunk)
        submission.mark_indexed()
        indexed = True
    except Exception:
        indexed = False

    await repository.save_submission(submission)

    return ApproveSubmissionResponse(id=submission.id, status="approved", indexed=indexed)


class RejectSubmissionRequest(BaseModel):
    reviewed_by: str
    reason: str | None = None


class RejectSubmissionResponse(BaseModel):
    id: UUID
    status: str
    reason: str | None = None


@router.post("/submissions/{submission_id}/reject")
async def reject_submission(
    submission_id: UUID,
    request: RejectSubmissionRequest,
    x_user_role: str = Header(...),
) -> RejectSubmissionResponse:
    """Reject a submission."""
    if x_user_role != "captain":
        raise HTTPException(status_code=403, detail="Only captain can reject submissions")

    from main import get_container

    container = get_container()
    repository = container.conversation_repository

    submission = await repository.get_submission(submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    submission.reject(reviewed_by=request.reviewed_by)
    await repository.save_submission(submission)

    return RejectSubmissionResponse(id=submission.id, status=submission.status.value, reason=request.reason)
