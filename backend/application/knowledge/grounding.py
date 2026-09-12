"""Grounded-answer helpers: keep replies exact when the KB has the fact."""

from __future__ import annotations

import re
from collections.abc import Sequence

from application.knowledge.retrieval import lexical_overlap_score
from domain.knowledge.value_objects import ChunkRef


_REFUSAL = re.compile(
    r"(?:the |these |those )?(?:provided |given )?"
    r"(?:documents?|context|knowledge[- ]base|passages?|sources?|information|text)\s+"
    r"(?:do(?:es)?\s+not|do(?:es)?n'?t)\s+"
    r"(?:contain|have|include|mention|provide|specify|state|say)"
    r"|(?:i\s+)?(?:do not|don'?t|can\s?not|can'?t)\s+(?:have|find|determine|answer|know)"
    r"|no (?:relevant )?information"
    r"|not (?:mentioned|available|found|provided|present|stated|specified)"
    r"|unable to (?:find|answer|determine)",
    re.IGNORECASE,
)

_HEADER_PREFIXES = ("subject:", "title:", "this is an indexed")

GREETING_REPLY = (
    "Hi, how are you? I am Dagmawi Teferi's assistant. "
    "Ask me about his skills, experience, education, or projects."
)

HOW_ARE_YOU_REPLY = (
    "I am fine, thank you for asking. "
    "Ask me anything about Dagmawi Teferi's background, experience, or projects."
)


def small_talk_reply(query: str) -> str:
    """A conversational reply for a greeting; it states no facts about anyone."""
    lowered = query.strip().lower()
    if any(phrase in lowered for phrase in ("how are you", "how r u", "how are u", "how do you do")):
        return HOW_ARE_YOU_REPLY
    return GREETING_REPLY


# Reason recorded when retrieval returns passages but none of them hold the fact.
NO_ANSWER_REASON = "The knowledge base does not contain this fact"

# Distinct from the above: the knowledge base may well hold the answer, but the
# model could not be reached to read it.
LLM_UNAVAILABLE_REASON = "The language model is unavailable"

# Retrieval always returns the top of a small KB, so a score floor is what
# separates "evidence" from "the least unrelated passage we happen to have".
MIN_EVIDENCE_SCORE = 0.15


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
    relevant = [chunk for chunk in ranked if score(chunk) >= MIN_EVIDENCE_SCORE]
    return relevant[: max(1, limit)]


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
- If a document says how to reply to a greeting or to small talk, follow that
  instruction and answer conversationally.
- If no document states the answer, reply exactly: "The documents do not contain that information."
  Do this even when the documents are about the same person or topic — being related to the
  question is not the same as answering it. Never substitute a different fact for the one asked.

Question: {query}

{joined}

Answer:"""
