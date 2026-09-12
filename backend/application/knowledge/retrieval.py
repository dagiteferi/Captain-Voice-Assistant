"""Index-time and query-time helpers so new KB facts stay retrievable."""

from __future__ import annotations

import re

from domain.knowledge.entities import Chunk, KnowledgeSubmission
from application.ports.vector_store_port import VectorStorePort

PROFILE_SUBJECT = "Dagmawi Teferi"
PROFILE_ALIASES = ("Dagi", "Dagmawi", "Dagiteferi")

_WORD = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_STOP = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "in",
        "at",
        "to",
        "of",
        "and",
        "or",
        "for",
        "on",
        "with",
        "what",
        "when",
        "where",
        "who",
        "how",
        "does",
        "did",
        "do",
        "about",
        "his",
        "her",
        "this",
        "that",
    }
)


def indexable_text(content: str, title: str | None = None) -> str:
    """Prefix facts so first-person notes still match name/nickname queries."""
    header = (
        f"Subject: {PROFILE_SUBJECT} (also known as {', '.join(PROFILE_ALIASES)}).\n"
        "This is an indexed knowledge fact about that person.\n"
    )
    if title:
        header += f"Title: {title}\n"
    return f"{header}\n{content.strip()}"


def expand_search_queries(query: str) -> list[str]:
    q = query.strip()
    if not q:
        return []
    queries = [q]
    lowered = q.lower()
    if "dagi" in lowered and "dagmawi" not in lowered:
        queries.append(re.sub(r"dagi", PROFILE_SUBJECT, q, flags=re.IGNORECASE))
    tokens = [token for token in query_tokens(q) if token not in {"dagi", "dagmawi", "teferi"}]
    if tokens:
        queries.append(f"{PROFILE_SUBJECT} {' '.join(tokens)}")
    seen: list[str] = []
    for item in queries:
        if item not in seen:
            seen.append(item)
    return seen


def query_tokens(text: str) -> set[str]:
    return {m.group(0).lower() for m in _WORD.finditer(text)} - _STOP


def lexical_overlap_score(query: str, document: str) -> float:
    q_tokens = query_tokens(query)
    if not q_tokens:
        return 0.0
    d_tokens = query_tokens(document)
    overlap = q_tokens & d_tokens
    base = len(overlap) / len(q_tokens)
    years_q = {t for t in q_tokens if t.isdigit() and len(t) == 4}
    years_d = {t for t in d_tokens if t.isdigit() and len(t) == 4}
    if years_q & years_d:
        base += 0.25
    birth_q = bool({"born", "birth", "birthday"} & q_tokens)
    birth_d = bool({"born", "birth", "birthday", "birthplace"} & d_tokens) or bool(years_d)
    if birth_q and birth_d:
        base += 0.4
    return min(base, 1.5)


async def upsert_submission_chunk(
    vector_store: VectorStorePort,
    submission: KnowledgeSubmission,
    title: str | None = None,
) -> None:
    await vector_store.delete_by_document_id(submission.id)
    chunk = Chunk(
        document_id=submission.id,
        content=indexable_text(submission.raw_content, title=title),
    )
    await vector_store.upsert(chunk)
