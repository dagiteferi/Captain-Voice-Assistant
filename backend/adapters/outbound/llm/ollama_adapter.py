"""Local LLM adapter using Ollama."""


class OllamaAdapter:
    async def generate(self, prompt: str, *, system_prompt: str | None = None) -> str:
        return f"Generated response for: {prompt}"
