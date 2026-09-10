"""Application command for submitting a Captain command."""

from dataclasses import dataclass


@dataclass
class SubmitCaptainCommand:
    text: str
    language: str | None = None
    user_id: str | None = None


class SubmitCaptainCommandHandler:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator

    async def handle(self, command: SubmitCaptainCommand):
        return await self.orchestrator.execute(command)
