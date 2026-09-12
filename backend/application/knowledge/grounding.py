"""Grounded-answer helpers: keep replies exact when the KB has the fact."""

from __future__ import annotations

import re
from collections.abc import Sequence

from application.knowledge.retrieval import lexical_overlap_score
from domain.knowledge.value_objects import ChunkRef

_REFUSAL = re.compile(
    r"(do not (contain|have|include|mention)"
    r"|does not (contain|have|include|mention)"
    r"|don't have"
    r"|doesn'?t have"
    r"|no (relevant )?information"
    r"|not (mentioned|available|found|provided|present|stated)"
    r"|unable to (find|answer|determine)"
    r"|cannot (find|determine|answer)"
    r"|i don'?t know"
    r"|the (provided )?documents do not)",
    re.IGNORECASE,
)

_HEADER_PREFIXES = ("subject:", "title:", "this is an indexed")


def strip_index_header(content: str) -> str:
    body: list[str] = []
    skipping = True
    for line in content.splitlines():
        lowered = line.strip().lower()
        if skipping and (not lowered or lowered.startswith(_HEADER_PREFIXES)):
            continue
        skipping = False
        body.append(line)
    return "\n".join(body).strip() or content.strip()


def looks_like_refusal(text: str) -> bool:
    return bool(text and _REFUSAL.search(text))


def select_evidence_chunks(
    query: str,
    chunks: Sequence[ChunkRef],
    *,
    limit: int = 4,
) -> list[ChunkRef]:
    if not chunks:
        return []

    def score(chunk: ChunkRef) -> float:
        lexical = lexical_overlap_score(query, chunk.content)
        return max(chunk.similarity_score, lexical)

    ranked = sorted(chunks, key=score, reverse=True)
    return ranked[: max(1, limit)]


def extractive_answer(query: str, chunks: Sequence[ChunkRef]) -> str | None:
    """Return the best matching KB passage verbatim when the LLM refuses."""
    if not chunks:
        return None
    best = max(
        chunks,
        key=lambda chunk: max(
            chunk.similarity_score,
            lexical_overlap_score(query, chunk.content),
        ),
    )
    lexical = lexical_overlap_score(query, best.content)
    if lexical < 0.08 and best.similarity_score < 0.28:
        return None
    return strip_index_header(best.content)


def build_generate_prompt(query: str, chunks: Sequence[ChunkRef]) -> str:
    documents = []
    for index, chunk in enumerate(chunks, start=1):
        documents.append(f"Document {index}:\n{strip_index_header(chunk.content)}")
    joined = "\n\n".join(documents)
    return f"""Answer the question using the knowledge-base documents below.

Rules:
- If ANY document contains the fact, you MUST answer with those exact facts (names, dates, GPA, places, numbers, employers, project titles).
- Prefer quoting or closely paraphrasing the document. Do not invent extra details.
- First-person text ("I was born") is about Dagmawi Teferi (Dagi).
- Say you do not have the information ONLY if none of the documents relate to the question.

Question: {query}

{joined}

Answer:"""
