"""Domain entities for the conversation aggregate."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Command:
    text: str
    language: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GroundedAnswer:
    answer: str
    citations: list[str] = field(default_factory=list)
    confidence: float = 0.0
    language: str = "en"
