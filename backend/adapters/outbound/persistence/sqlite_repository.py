"""SQLite-backed conversation repository."""


class SQLiteRepository:
    async def get_trace(self, conversation_id: str):
        return {"conversation_id": conversation_id, "trace": []}

    async def save(self, conversation):
        return conversation
