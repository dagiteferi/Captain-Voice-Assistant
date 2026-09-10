"""Knowledge base entities."""

from dataclasses import dataclass, field


@dataclass
class Document:
    id: str
    title: str
    content: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class Chunk:
    id: str
    document_id: str
    text: str
    embedding: list[float] | None = None
    metadata: dict[str, str] = field(default_factory=dict)
