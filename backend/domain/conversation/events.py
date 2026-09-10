"""Domain events emitted during the conversational pipeline."""

from dataclasses import dataclass
from typing import Any


@dataclass
class RetrievalCompleted:
    query: str
    results: list[dict[str, Any]]


@dataclass
class AnswerGrounded:
    answer: str
    citations: list[str]
    confidence: float


@dataclass
class PipelineStarted:
    command_id: str


@dataclass
class PipelineFinished:
    command_id: str
    status: str
