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


# Greetings carry almost no searchable text, so "hello" alone never matches a
# knowledge entry written as "when you ask hi ...". Every greeting is therefore
# also searched under one shared phrasing.
GREETING_QUERY = "greeting hi hello how are you reply"

_GREETING_WORDS = frozenset(
    {
        "hi",
        "hii",
        "hiii",
        "hey",
        "heyy",
        "hello",
        "helo",
        "hallo",
        "yo",
        "greetings",
        "morning",
        "afternoon",
        "evening",
        "selam",
        "salam",
        "tena",
        "yistilign",
        "there",
        "you",
        "u",
        "good",
        "day",
    }
)

_SMALL_TALK_PHRASES = (
    "how are you",
    "how r u",
    "how are u",
    "how do you do",
    "how is it going",
    "how's it going",
    "whats up",
    "what's up",
    "good morning",
    "good afternoon",
    "good evening",
)


def is_small_talk(query: str) -> bool:
    """True for greetings and pleasantries rather than questions about facts."""
    lowered = query.strip().lower().strip("?!.,")
    if not lowered:
        return False
    if any(phrase in lowered for phrase in _SMALL_TALK_PHRASES):
        return True
    tokens = [m.group(0) for m in _WORD.finditer(lowered)]
    if not tokens or len(tokens) > 3:
        return False
    return all(token in _GREETING_WORDS for token in tokens)


def expand_search_queries(query: str) -> list[str]:
    q = query.strip()
    if not q:
        return []
    if is_small_talk(q):
        # Widening a greeting with the profile subject only drags in CV chunks.
        return [q, GREETING_QUERY]
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
    # "how old is he" must reach a passage that only says "born in 1999".
    birth_q = bool({"born", "birth", "birthday", "age", "old", "aged"} & q_tokens)
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
