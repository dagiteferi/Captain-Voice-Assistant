from uuid import uuid4

from application.knowledge.grounding import (
    extractive_answer,
    looks_like_refusal,
    select_evidence_chunks,
    strip_index_header,
)
from domain.knowledge.value_objects import ChunkRef


def _chunk(content: str, score: float = 0.2) -> ChunkRef:
    return ChunkRef(
        chunk_id=uuid4(),
        document_id=uuid4(),
        content=content,
        similarity_score=score,
    )


def test_strip_index_header_keeps_fact_text():
    raw = (
        "Subject: Dagmawi Teferi (also known as Dagi, Dagmawi, Dagiteferi).\n"
        "This is an indexed knowledge fact about that person.\n"
        "Title: Birthplace and year of birth\n"
        "\n"
        "Dagmawi Teferi (Dagi) was born in 1999 in Adama, Ethiopia."
    )
    assert strip_index_header(raw) == "Dagmawi Teferi (Dagi) was born in 1999 in Adama, Ethiopia."


def test_looks_like_refusal_detects_missing_info_replies():
    assert looks_like_refusal("The provided documents do not contain information about GPA.")
    assert not looks_like_refusal("Dagmawi Teferi was born in 1999 in Adama.")


def test_select_evidence_prefers_matching_fact_over_generic_cv():
    query = "what is dagmawi teferi GPA"
    birth = _chunk("Dagmawi Teferi earned GPA 3.94 at Unity University.", 0.22)
    generic = _chunk("Dagmawi Teferi builds FastAPI microservices and RAG pipelines.", 0.81)
    selected = select_evidence_chunks(query, [generic, birth], limit=1)
    assert "3.94" in selected[0].content


def test_extractive_answer_returns_exact_kb_passage():
    query = "when was dagi born"
    chunks = [
        _chunk("He developed RAG pipelines for finance.", 0.4),
        _chunk(
            "Subject: Dagmawi Teferi (also known as Dagi).\n\n"
            "Dagmawi Teferi was born in 1999 in Adama.",
            0.3,
        ),
    ]
    answer = extractive_answer(query, chunks)
    assert answer == "Dagmawi Teferi was born in 1999 in Adama."
