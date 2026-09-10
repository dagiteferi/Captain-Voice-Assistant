"""Application query for reading the conversation trace."""

from dataclasses import dataclass


@dataclass
class GetConversationTraceQuery:
    conversation_id: str


class GetConversationTraceHandler:
    def __init__(self, repository):
        self.repository = repository

    async def handle(self, query: GetConversationTraceQuery):
        return await self.repository.get_trace(query.conversation_id)
