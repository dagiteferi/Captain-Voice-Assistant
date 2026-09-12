from uuid import uuid4

from application.knowledge.grounding import (
    looks_like_refusal,
    small_talk_reply,
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
    assert looks_like_refusal("His age is not stated in the knowledge base.")
    assert looks_like_refusal("I don't have that information.")
    assert not looks_like_refusal("Dagmawi Teferi was born in 1999 in Adama.")


def test_negation_about_the_subject_is_not_a_refusal():
    # A genuinely negative answer must survive; only refusals about the
    # source material should route the pipeline to fallback.
    assert not looks_like_refusal("Dagmawi Teferi does not have a PhD.")
    assert not looks_like_refusal("He doesn't have experience with Rust.")


def test_select_evidence_prefers_matching_fact_over_generic_cv():
    query = "what is dagmawi teferi GPA"
    birth = _chunk("Dagmawi Teferi earned GPA 3.94 at Unity University.", 0.22)
    generic = _chunk("Dagmawi Teferi builds FastAPI microservices and RAG pipelines.", 0.81)
    selected = select_evidence_chunks(query, [generic, birth], limit=1)
    assert "3.94" in selected[0].content


def test_select_evidence_drops_passages_below_the_relevance_floor():
    strong = _chunk("Dagmawi Teferi earned GPA 3.94 at Unity University.", 0.62)
    noise = _chunk("Unrelated note about shipping containers.", 0.02)
    selected = select_evidence_chunks("what is dagmawi teferi GPA", [strong, noise], limit=4)
    assert selected == [strong]


def test_select_evidence_returns_nothing_when_all_passages_are_noise():
    noise = [_chunk("Unrelated note about shipping containers.", 0.01)]
    assert select_evidence_chunks("what is the GPA", noise) == []


def test_small_talk_reply_greets_without_stating_facts():
    greeting = small_talk_reply("hii")
    assert "how are you" in greeting.lower()
    assert small_talk_reply("how are you?").lower().startswith("i am fine")
