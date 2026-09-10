"""Vector store adapter using Chroma."""


class ChromaAdapter:
    async def search(self, query: str, *, limit: int = 5) -> list[dict]:
        return [{"id": "doc-1", "text": f"Search result for: {query}", "score": 0.99}]
