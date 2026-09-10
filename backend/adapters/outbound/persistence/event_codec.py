from __future__ import annotations

import json
from dataclasses import fields, is_dataclass
from datetime import datetime
from typing import Any, get_args, get_origin, get_type_hints
from uuid import UUID

from domain.conversation.events import (
    AnswerGrounded,
    AudioResponseReady,
    PipelineFallback,
    RetrievalCompleted,
)
from domain.conversation.value_objects import Language
from domain.events import DomainEvent
from domain.knowledge.events import (
    KnowledgeIndexed,
    KnowledgeSubmissionApproved,
    KnowledgeSubmissionQueued,
    KnowledgeSubmissionRejected,
)
from domain.voice.events import AudioSynthesized, TranslationCompleted

EVENT_TYPES: dict[str, type[DomainEvent]] = {
    cls.__name__: cls
    for cls in (
        RetrievalCompleted,
        AnswerGrounded,
        PipelineFallback,
        AudioResponseReady,
        TranslationCompleted,
        AudioSynthesized,
        KnowledgeSubmissionQueued,
        KnowledgeSubmissionApproved,
        KnowledgeSubmissionRejected,
        KnowledgeIndexed,
    )
}


def dump_event(event: DomainEvent) -> tuple[str, str]:
    payload: dict[str, Any] = {}
    for item in fields(event):
        if item.name == "occurred_at":
            continue
        payload[item.name] = _to_jsonable(getattr(event, item.name))
    return type(event).__name__, json.dumps(payload)


def load_event(event_type: str, payload_json: str, occurred_at: datetime) -> DomainEvent:
    cls = EVENT_TYPES[event_type]
    raw = json.loads(payload_json)
    hints = get_type_hints(cls)
    kwargs: dict[str, Any] = {"occurred_at": occurred_at}
    for name, typ in hints.items():
        if name == "occurred_at":
            continue
        kwargs[name] = _from_jsonable(typ, raw[name])
    return cls(**kwargs)


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Language):
        return value.code
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if is_dataclass(value):
        return {item.name: _to_jsonable(getattr(value, item.name)) for item in fields(value)}
    return value


def _from_jsonable(typ: Any, value: Any) -> Any:
    origin = get_origin(typ)
    if origin is tuple:
        (inner, *rest) = get_args(typ)
        return tuple(_from_jsonable(inner, item) for item in value)
    if typ is UUID:
        return UUID(value)
    if typ is Language:
        return Language(value)
    if typ is datetime:
        return datetime.fromisoformat(value)
    return value
