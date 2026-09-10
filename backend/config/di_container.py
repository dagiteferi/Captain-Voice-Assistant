"""Dependency injection container for adapters and ports."""

from adapters.outbound.llm.ollama_adapter import OllamaAdapter
from adapters.outbound.translation.argos_adapter import ArgoAdapter
from adapters.outbound.tts.coqui_adapter import CoquiAdapter
from adapters.outbound.vector_store.chroma_adapter import ChromaAdapter


class DIContainer:
    def __init__(self):
        self.llm = OllamaAdapter()
        self.vector_store = ChromaAdapter()
        self.translator = ArgoAdapter()
        self.tts = CoquiAdapter()

    def build_orchestrator(self):
        from adapters.outbound.orchestration.orchestrator_agent import OrchestratorAgent

        return OrchestratorAgent(
            llm=self.llm,
            vector_store=self.vector_store,
            translator=self.translator,
            tts=self.tts,
            publisher=None,
        )
