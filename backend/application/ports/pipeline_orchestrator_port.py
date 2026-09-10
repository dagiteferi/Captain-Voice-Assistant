"""Port for pipeline orchestration."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class PipelineOrchestratorPort(Protocol):
    async def execute(self, command):
        ...
