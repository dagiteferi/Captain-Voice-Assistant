"""State objects for orchestration workflow execution."""

from dataclasses import dataclass, field


@dataclass
class OrchestrationState:
    command_id: str
    status: str = "queued"
    trace: list[str] = field(default_factory=list)
