"""Knowledge base API routes."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Header, status
from pydantic import BaseModel

from application.knowledge.seed_documents import SAMPLE_DOCUMENTS as INITIAL_KNOWLEDGE_DOCS

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


async def _process_and_save_submission(
    submitted_by: str,
    submitter_role_str: str,
    raw_content: str,
    title_prefix: str = "Submission",
) -> SubmitKnowledgeResponse:
    from main import get_container
    from domain.knowledge.entities import KnowledgeSubmission, Document, Chunk
    from domain.knowledge.value_objects import SubmitterRole
    from domain.knowledge.rules import evaluate_submission
    from uuid import uuid4

    container = get_container()
    repository = container.conversation_repository

    submitter_role = SubmitterRole(submitter_role_str)
    submission = KnowledgeSubmission(
        submitted_by=submitted_by,
        submitter_role=submitter_role,
        raw_content=raw_content,
    )

    hits = await container.vector_store.search(raw_content, limit=1)
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
            title=f"{title_prefix} {submission.id}",
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


@router.post("/submissions", status_code=status.HTTP_201_CREATED)
async def submit_knowledge(
    request: SubmitKnowledgeRequest,
) -> SubmitKnowledgeResponse:
    """Method 1: Propose raw text content for the knowledge base."""
    return await _process_and_save_submission(
        submitted_by=request.submitted_by,
        submitter_role_str=request.submitter_role,
        raw_content=request.raw_content,
    )


from fastapi import UploadFile, File, Form


@router.post("/submissions/file", status_code=status.HTTP_201_CREATED)
async def submit_knowledge_file(
    file: UploadFile = File(...),
    submitted_by: str = Form("Captain"),
    submitter_role: str = Form("captain"),
) -> SubmitKnowledgeResponse:
    """Method 2: Upload file (PDF, Word, PPT, Text, CSV, JSON) to extract and propose knowledge."""
    from application.knowledge.file_parser import extract_text_from_file

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        extracted_text = extract_text_from_file(file.filename or "file.txt", file_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    content_with_meta = f"# Source File: {file.filename}\n\n{extracted_text}"
    return await _process_and_save_submission(
        submitted_by=submitted_by,
        submitter_role_str=submitter_role,
        raw_content=content_with_meta,
        title_prefix=f"File ({file.filename})",
    )


class SubmitUrlRequest(BaseModel):
    submitted_by: str
    submitter_role: str
    url: str


@router.post("/submissions/url", status_code=status.HTTP_201_CREATED)
async def submit_knowledge_url(
    request: SubmitUrlRequest,
) -> SubmitKnowledgeResponse:
    """Method 3: Ingest knowledge from a web page / URL."""
    from application.knowledge.file_parser import extract_text_from_url

    try:
        extracted_text = await extract_text_from_url(request.url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch content from URL: {e}")

    content_with_meta = f"# Source URL: {request.url}\n\n{extracted_text}"
    return await _process_and_save_submission(
        submitted_by=request.submitted_by,
        submitter_role_str=request.submitter_role,
        raw_content=content_with_meta,
        title_prefix=f"URL ({request.url})",
    )


class SubmitProcedureRequest(BaseModel):
    submitted_by: str
    submitter_role: str
    title: str
    category: str
    severity: str
    steps: list[str]
    notes: str | None = None


@router.post("/submissions/procedure", status_code=status.HTTP_201_CREATED)
async def submit_knowledge_procedure(
    request: SubmitProcedureRequest,
) -> SubmitKnowledgeResponse:
    """Method 4: Propose a structured Standard Operating Procedure (SOP)."""
    formatted_steps = "\n".join([f"{i+1}. {step}" for i, step in enumerate(request.steps) if step.strip()])
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


class UpdateSubmissionRequest(BaseModel):
    raw_content: str


async def _ensure_initial_knowledge_seeded(container):
    repository = container.conversation_repository
    submissions = await repository.list_submissions()
    if submissions:
        return

    from uuid import uuid4
    from datetime import datetime, timezone
    from domain.knowledge.entities import KnowledgeSubmission, Document, Chunk
    from domain.knowledge.value_objects import SubmitterRole, SubmissionStatus

    for doc in INITIAL_KNOWLEDGE_DOCS:
        sub_id = uuid4()
        raw_content = f"# {doc['title']}\n\n{doc['content']}"
        sub = KnowledgeSubmission(
            id=sub_id,
            submitted_by="system_seeder",
            submitter_role=SubmitterRole.CAPTAIN,
            raw_content=raw_content,
            status=SubmissionStatus.APPROVED,
            rule_results=[{"rule": "AutoSeeded", "outcome": "pass"}],
            created_at=datetime.now(timezone.utc),
            reviewed_by="captain",
        )
        await repository.save_submission(sub)

        # Index into vector store as well
        document = Document(id=sub_id, title=doc['title'], source_path=f"seed/{sub_id}")
        chunk = Chunk(id=uuid4(), document_id=document.id, content=raw_content)
        await container.vector_store.upsert(chunk)


@router.get("/manage")
async def list_manage_knowledge(
    x_user_role: str = Header(...),
):
    """List all knowledge base items for management (Captain & Crew)."""
    if x_user_role not in ("captain", "crew"):
        raise HTTPException(status_code=403, detail="Access denied")

    from main import get_container
    container = get_container()
    repository = container.conversation_repository

    submissions = await repository.list_submissions()
    if not submissions:
        await _ensure_initial_knowledge_seeded(container)
        submissions = await repository.list_submissions()

    items = [
        {
            "id": str(s.id),
            "submitted_by": s.submitted_by,
            "submitter_role": s.submitter_role.value,
            "raw_content": s.raw_content,
            "status": s.status.value,
            "created_at": s.created_at.isoformat(),
        }
        for s in submissions
    ]
    return {"items": items, "count": len(items)}


@router.put("/manage/{submission_id}")
async def update_knowledge_item(
    submission_id: UUID,
    request: UpdateSubmissionRequest,
    x_user_role: str = Header(...),
):
    """Update knowledge item content and re-index in vector store."""
    if x_user_role not in ("captain", "crew"):
        raise HTTPException(status_code=403, detail="Access denied")

    from main import get_container
    from domain.knowledge.entities import Document, Chunk
    from uuid import uuid4

    container = get_container()
    repository = container.conversation_repository

    submission = await repository.get_submission(submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Knowledge item not found")

    submission.raw_content = request.raw_content.strip()
    await repository.save_submission(submission)

    # Re-index in Chroma vector store if approved
    if submission.status.value == "approved":
        await container.vector_store.delete_by_document_id(submission.id)
        doc = Document(id=submission.id, title=f"Submission {submission.id}", source_path=f"submissions/{submission.id}")
        chunk = Chunk(id=uuid4(), document_id=doc.id, content=submission.raw_content)
        await container.vector_store.upsert(chunk)

    return {"status": "ok", "message": "Knowledge item updated and re-indexed."}


@router.delete("/manage/{submission_id}")
async def delete_knowledge_item(
    submission_id: UUID,
    x_user_role: str = Header(...),
):
    """Delete knowledge item from DB and remove its vector embeddings."""
    if x_user_role != "captain":
        raise HTTPException(status_code=403, detail="Only captain can delete knowledge items")

    from main import get_container
    container = get_container()
    repository = container.conversation_repository

    submission = await repository.get_submission(submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Knowledge item not found")

    # Remove embeddings from vector store
    await container.vector_store.delete_by_document_id(submission.id)

    # Delete row from DB
    async with repository._session_factory() as session:
        async with session.begin():
            from adapters.outbound.persistence.models import KnowledgeSubmissionModel
            row = await session.get(KnowledgeSubmissionModel, submission_id)
            if row:
                await session.delete(row)

    return {"status": "ok", "message": "Knowledge item deleted."}


@router.get("/presets")
async def get_knowledge_presets():
    """Get dynamic preset queries derived ONLY from items present in Knowledge Management."""
    from main import get_container
    container = get_container()
    repository = container.conversation_repository

    submissions = await repository.list_submissions()
    if not submissions:
        await _ensure_initial_knowledge_seeded(container)
        submissions = await repository.list_submissions()

    presets = []
    for s in submissions:
        lines = [line.strip('# ').strip() for line in s.raw_content.split('\n') if line.strip()]
        if lines:
            title = lines[0]
            if len(title) > 60:
                title = title[:57] + "..."
            if title and title not in presets:
                presets.append(title)

    return {"presets": presets[:8]}


