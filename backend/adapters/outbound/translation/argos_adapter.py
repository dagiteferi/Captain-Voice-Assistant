"""Default local translation adapter."""


class ArgoAdapter:
    async def translate(self, text: str, *, source_language: str, target_language: str) -> str:
        return text
