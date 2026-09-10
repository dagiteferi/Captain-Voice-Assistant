"""Pipeline orchestrator implementation."""


class OrchestratorAgent:
    def __init__(self, llm, vector_store, translator, tts, publisher):
        self.llm = llm
        self.vector_store = vector_store
        self.translator = translator
        self.tts = tts
        self.publisher = publisher

    async def execute(self, command):
        return {
            "status": "queued",
            "command": getattr(command, "text", str(command)),
        }
