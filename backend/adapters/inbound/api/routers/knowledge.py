"""Knowledge base API routes."""

from uuid import UUID

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile, status
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
    # How many chunks were indexed — also how many embedding requests it cost.
    indexed_chunks: int = 0


@router.post("/submissions", status_code=status.HTTP_201_CREATED)
async def submit_knowledge(
    request: SubmitKnowledgeRequest,
) -> SubmitKnowledgeResponse:
    """Propose new information for the knowledge base."""
    return await _process_and_save_submission(
        submitted_by=request.submitted_by,
        submitter_role_str=request.submitter_role,
        raw_content=request.raw_content,
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
        status=status_result.value,
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
    
    # Index the submission into the vector store
    try:
        doc = Document(id=uuid4(), title=f"Submission {submission_id}", source_path=f"submissions/{submission_id}")
        chunk = Chunk(document_id=doc.id, content=submission.raw_content)
        
        # Index chunk into vector store
        await container.vector_store.upsert(chunk)
        
        # Mark submission as indexed
        submission.mark_indexed()
    except Exception as e:
        # If indexing fails, keep as approved but not indexed
        pass

    await repository.save_submission(submission)

    return ApproveSubmissionResponse(id=submission.id, status=submission.status.value, indexed=True)


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


class SubmitUrlRequest(BaseModel):
    submitted_by: str
    submitter_role: str
    url: str


class SubmitProcedureRequest(BaseModel):
    submitted_by: str
    submitter_role: str
    title: str
    category: str
    severity: str
    steps: list[str]
    notes: str | None = None


async def _process_and_save_submission(
    submitted_by: str,
    submitter_role_str: str,
    raw_content: str,
    title_prefix: str = "Submission",
) -> SubmitKnowledgeResponse:
    """Run a submission through the rule chain, indexing it when auto-approved."""
    from main import get_container
    from application.knowledge.retrieval import upsert_submission_chunk
    from domain.knowledge.entities import KnowledgeSubmission
    from domain.knowledge.rules import evaluate_submission
    from domain.knowledge.value_objects import SubmitterRole

    container = get_container()
    repository = container.conversation_repository

    submitter_role = SubmitterRole(submitter_role_str)
    submission = KnowledgeSubmission(
        submitted_by=submitted_by,
        submitter_role=submitter_role,
        raw_content=raw_content,
    )

    # Duplicate detection wants "how alike is this text", which is the cosine,
    # not the keyword-boosted ranking score that made every long upload look
    # like a perfect duplicate.
    hits = await container.vector_store.search(raw_content, limit=1)
    max_similarity = hits[0].cosine_score if hits else 0.0
    status_result, rule_results = evaluate_submission(
        submission,
        submitter_role,
        similarity_fn=lambda _: max_similarity,
    )
    submission.status = status_result
    submission.record_rule_results(rule_results)

    indexed_chunks = 0
    if status_result.value == "approved":
        chunks = await upsert_submission_chunk(
            container.vector_store,
            submission,
            title=f"{title_prefix} {submission.id}",
        )
        indexed_chunks = len(chunks)
        submission.mark_indexed()

    await repository.save_submission(submission)

    return SubmitKnowledgeResponse(
        submission_id=submission.id,
        status=status_result.value,
        rule_results=[RuleResultItem(**r) for r in rule_results],
        indexed_chunks=indexed_chunks,
    )


@router.post("/submissions/file", status_code=status.HTTP_201_CREATED)
async def submit_knowledge_file(
    file: UploadFile = File(...),
    submitted_by: str = Form("Captain"),
    submitter_role: str = Form("captain"),
) -> SubmitKnowledgeResponse:
    """Extract knowledge from an uploaded document (PDF, Word, PPT, text, CSV, JSON)."""
    from application.knowledge.file_parser import extract_text_from_file

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        extracted_text = extract_text_from_file(file.filename or "file.txt", file_bytes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return await _process_and_save_submission(
        submitted_by=submitted_by,
        submitter_role_str=submitter_role,
        raw_content=f"# Source File: {file.filename}\n\n{extracted_text}",
        title_prefix=f"File ({file.filename})",
    )


@router.post("/submissions/url", status_code=status.HTTP_201_CREATED)
async def submit_knowledge_url(request: SubmitUrlRequest) -> SubmitKnowledgeResponse:
    """Ingest knowledge from a web page."""
    from application.knowledge.file_parser import extract_text_from_url

    try:
        extracted_text = await extract_text_from_url(request.url)
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail=f"Failed to fetch content from URL: {exc}"
        ) from exc

    return await _process_and_save_submission(
        submitted_by=request.submitted_by,
        submitter_role_str=request.submitter_role,
        raw_content=f"# Source URL: {request.url}\n\n{extracted_text}",
        title_prefix=f"URL ({request.url})",
    )


@router.post("/submissions/procedure", status_code=status.HTTP_201_CREATED)
async def submit_knowledge_procedure(
    request: SubmitProcedureRequest,
) -> SubmitKnowledgeResponse:
    """Propose a structured Standard Operating Procedure."""
    formatted_steps = "\n".join(
        f"{index + 1}. {step}"
        for index, step in enumerate(step for step in request.steps if step.strip())
    )
    content = (
        f"# SOP: {request.title}\n"
        f"**Category:** {request.category} | **Severity Level:** {request.severity}\n\n"
        f"## Standard Operating Steps:\n"
        f"{formatted_steps}\n"
    )
    if request.notes:
        content += f"\n## Operational Notes & Safety Warnings:\n{request.notes}\n"

    return await _process_and_save_submission(
        submitted_by=request.submitted_by,
        submitter_role_str=request.submitter_role,
        raw_content=content,
        title_prefix=f"SOP ({request.title})",
    )


class UpdateKnowledgeItemRequest(BaseModel):
    raw_content: str


@router.get("/manage")
async def list_manage_knowledge(x_user_role: str = Header(...)):
    """List every knowledge item for the management screen."""
    if x_user_role not in ("captain", "crew"):
        raise HTTPException(status_code=403, detail="Access denied")

    from main import get_container

    container = get_container()
    submissions = await container.conversation_repository.list_submissions()

    items = [
        {
            "id": str(item.id),
            "submitted_by": item.submitted_by,
            "submitter_role": item.submitter_role.value,
            "raw_content": item.raw_content,
            "status": item.status.value,
            "created_at": item.created_at.isoformat(),
        }
        for item in submissions
    ]
    return {"items": items, "count": len(items)}


@router.put("/manage/{submission_id}")
async def update_knowledge_item(
    submission_id: UUID,
    request: UpdateKnowledgeItemRequest,
    x_user_role: str = Header(...),
):
    """Edit a knowledge item and re-index it in the vector store."""
    if x_user_role not in ("captain", "crew"):
        raise HTTPException(status_code=403, detail="Access denied")

    from main import get_container
    from application.knowledge.retrieval import upsert_submission_chunk

    container = get_container()
    repository = container.conversation_repository

    submission = await repository.get_submission(submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Knowledge item not found")

    submission.raw_content = request.raw_content.strip()

    reindexed = submission.status.value in ("approved", "indexed")
    if reindexed:
        await upsert_submission_chunk(
            container.vector_store,
            submission,
            title=f"Submission {submission.id}",
        )
        if submission.status.value == "approved":
            submission.mark_indexed()

    await repository.save_submission(submission)

    return {
        "status": "ok",
        "reindexed": reindexed,
        "message": (
            "Knowledge item updated and re-indexed."
            if reindexed
            else "Knowledge item updated. It is indexed once approved."
        ),
    }


@router.delete("/manage/{submission_id}")
async def delete_knowledge_item(
    submission_id: UUID,
    x_user_role: str = Header(...),
):
    """Delete a knowledge item and drop its embeddings."""
    if x_user_role != "captain":
        raise HTTPException(status_code=403, detail="Only captain can delete knowledge items")

    from main import get_container

    container = get_container()
    repository = container.conversation_repository

    submission = await repository.get_submission(submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Knowledge item not found")

    await container.vector_store.delete_by_document_id(submission.id)
    await repository.delete_submission(submission_id)

    return {"status": "ok", "message": "Knowledge item deleted."}


@router.get("/presets")
async def get_knowledge_presets():
    """Preset questions derived from the titles of indexed knowledge items."""
    from main import get_container

    container = get_container()
    submissions = await container.conversation_repository.list_submissions()

    presets: list[str] = []
    for item in submissions:
        lines = [line.strip("# ").strip() for line in item.raw_content.split("\n") if line.strip()]
        if not lines:
            continue
        title = lines[0]
        if len(title) > 60:
            title = title[:57] + "..."
        if title and title not in presets:
            presets.append(title)

    return {"presets": presets[:8]}
