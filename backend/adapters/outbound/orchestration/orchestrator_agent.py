"""Flat LangGraph pipeline orchestrator implementation."""

import logging
from pathlib import Path
from typing import cast

from langgraph.graph import StateGraph, END

logger = logging.getLogger(__name__)


from adapters.outbound.orchestration.state import PipelineState
from application.ports.conversation_repository_port import ConversationRepositoryPort
from application.ports.event_publisher_port import EventPublisherPort
from application.ports.llm_port import LLMPort
from application.ports.pipeline_orchestrator_port import PipelineOrchestratorPort, PipelineOutcome
from application.ports.translator_port import TranslatorPort
from application.ports.tts_port import TTSPort
from application.ports.vector_store_port import VectorStorePort
from domain.conversation.entities import Command, GroundedAnswer
from domain.conversation.value_objects import Language, PipelineStatus, Citation
from domain.voice.entities import AudioResponse, Translation, CAPTAIN_PRESET
from domain.conversation.events import (
    RetrievalCompleted,
    AnswerGrounded,
    AudioResponseReady,
    PipelineFallback,
)
from domain.voice.events import TranslationCompleted
from domain.voice.events import AudioSynthesized


class FlatLangGraphOrchestrator:
    """Single flat LangGraph pipeline: retrieve → generate → verify-grounding → translate → synthesize."""

    def __init__(
        self,
        llm_port: LLMPort,
        vector_store_port: VectorStorePort,
        translator_port: TranslatorPort,
        tts_port: TTSPort,
        event_publisher: EventPublisherPort,
        repository: ConversationRepositoryPort,
        audio_dir: str | Path = "./data/audio",
    ):
        self.llm_port = llm_port
        self.vector_store_port = vector_store_port
        self.translator_port = translator_port
        self.tts_port = tts_port
        self.event_publisher = event_publisher
        self.repository = repository
        self.audio_dir = Path(audio_dir)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self._graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Construct the LangGraph state machine."""
        graph = StateGraph(PipelineState)

        graph.add_node("retrieve", self._node_retrieve)
        graph.add_node("grade_docs", self._node_grade_docs)
        graph.add_node("generate", self._node_generate)
        graph.add_node("verify_ground", self._node_verify_ground)
        graph.add_node("translate", self._node_translate)
        graph.add_node("synthesize", self._node_synthesize)
        graph.add_node("fallback", self._node_fallback)

        graph.set_entry_point("retrieve")

        # retrieve → grade_docs
        graph.add_edge("retrieve", "grade_docs")

        # grade_docs: if relevant, go to generate; else fallback
        graph.add_conditional_edges(
            "grade_docs",
            lambda state: "generate" if state.retrieval_relevant else "fallback",
        )

        # generate → verify_ground
        graph.add_edge("generate", "verify_ground")

        # verify_ground: if grounded, translate; else fallback
        graph.add_conditional_edges(
            "verify_ground",
            lambda state: "translate" if state.grounded_answer else "fallback",
        )

        # translate → synthesize
        graph.add_edge("translate", "synthesize")

        # synthesize → end
        graph.add_edge("synthesize", END)

        # fallback → end
        graph.add_edge("fallback", END)

        return graph.compile()

    async def execute(self, command: Command) -> PipelineOutcome:
        conversation = await self.repository.get_conversation(command.conversation_id)
        target_language = conversation.target_language.code if conversation else "en"
        state = PipelineState(
            command=command,
            target_language=target_language,
        )

        result = await self._graph.ainvoke(state)
        # LangGraph may return a dict of updated fields or the PipelineState instance
        if isinstance(result, dict):
            # merge into the original state object for compatibility
            for k, v in result.items():
                setattr(state, k, v)
            result = state
        else:
            result = cast(PipelineState, result)

        # Publish all captured events
        for event in result.events:
            await self.event_publisher.publish(event)

        # Persist the command and its artifacts
        command.status = result.status
        command.grounded_answer = result.grounded_answer
        await self.repository.save_command(command)

        if result.grounded_answer:
            await self.repository.save_grounded_answer(result.grounded_answer)
        if result.translation:
            await self.repository.save_translation(result.translation)
        if result.audio_response:
            await self.repository.save_audio_response(result.audio_response)

        for event in result.events:
            await self.repository.append_event(command.id, event)

        return PipelineOutcome(
            command=command,
            status=result.status,
            grounded_answer=result.grounded_answer,
            translation=result.translation,
            audio_response=result.audio_response,
            fallback_reason=result.fallback_reason,
        )

    async def _node_retrieve(self, state: PipelineState) -> dict:
        """Retrieve relevant chunks from vector store."""
        state.retrieval_attempts += 1
        chunks = await self.vector_store_port.search(state.command.input_text, limit=5)
        state.retrieved_chunks = chunks

        event = RetrievalCompleted(
            command_id=state.command.id,
            query=state.command.input_text,
            chunk_ids=tuple(c.chunk_id for c in chunks),
            similarity_scores=tuple(c.similarity_score for c in chunks),
            relevant=len(chunks) > 0,
        )
        state.events.append(event)
        state.retrieval_relevant = len(chunks) > 0

        return {"retrieved_chunks": chunks, "retrieval_relevant": len(chunks) > 0}

    async def _node_grade_docs(self, state: PipelineState) -> dict:
        """Grade whether retrieved chunks are actually relevant."""
        if not state.retrieved_chunks:
            return {"retrieval_relevant": False}

        prompt = f"""Evaluate whether these retrieved documents are relevant to the query.
Query: {state.command.input_text}
Documents:
{chr(10).join(f'- {c.content}' for c in state.retrieved_chunks)}
Respond with "RELEVANT" or "NOT_RELEVANT"."""

        response = await self.llm_port.generate(
            query=prompt,
            chunks=state.retrieved_chunks,
            system_prompt="You are a relevance grader. Respond only with RELEVANT or NOT_RELEVANT.",
        )

        relevant = "RELEVANT" in response.upper()
        return {"retrieval_relevant": relevant}

    async def _node_generate(self, state: PipelineState) -> dict:
        """Generate an answer grounded in retrieved chunks."""
        prompt = f"""Answer the following query using ONLY the provided documents. 
You MUST cite your sources by referencing the document snippets.
Query: {state.command.input_text}
Documents:
{chr(10).join(f'- {c.content}' for c in state.retrieved_chunks)}
Answer:"""

        answer_text = await self.llm_port.generate(
            query=prompt,
            chunks=state.retrieved_chunks,
            system_prompt="You are a helpful assistant. Answer using only the provided documents.",
        )

        citations = [Citation(chunk_id=c.chunk_id) for c in state.retrieved_chunks]
        grounded_answer = GroundedAnswer(
            command_id=state.command.id,
            answer_text=answer_text,
            citations=citations,
        )

        return {"grounded_answer": grounded_answer}

    async def _node_verify_ground(self, state: PipelineState) -> dict:
        """Verify that the answer has citations (grounding check)."""
        if not state.grounded_answer:
            return {"grounded_answer": None}

        try:
            state.grounded_answer.validate()
            state.status = PipelineStatus.GROUNDED

            event = AnswerGrounded(
                command_id=state.command.id,
                answer_id=state.grounded_answer.id,
                citations=tuple(state.grounded_answer.citations),
            )
            state.events.append(event)

            return {"grounded_answer": state.grounded_answer, "status": PipelineStatus.GROUNDED}
        except Exception:
            return {"grounded_answer": None, "status": PipelineStatus.UNGROUNDED}

    async def _node_translate(self, state: PipelineState) -> dict:
        """Translate the grounded answer to the target language.

        If the translator raises (e.g. missing language pack, passthrough
        detected), we record a fallback rather than emitting a false
        TranslationCompleted event.
        """
        if not state.grounded_answer:
            return {"translation": None}

        target_lang = Language(state.target_language)
        logger.info(
            "[translate] Translating answer (len=%d) to %s",
            len(state.grounded_answer.answer_text),
            target_lang.code,
        )

        try:
            translated_text = await self.translator_port.translate(
                state.grounded_answer.answer_text,
                target_lang,
            )
        except Exception as e:
            logger.error(
                "[translate] Translation FAILED — recording pipeline failure. Error: %s", e
            )
            state.fallback_reason = f"Translation failed: {e}"
            state.status = PipelineStatus.FAILED
            return {"translation": None, "status": PipelineStatus.FAILED, "fallback_reason": state.fallback_reason}

        logger.info(
            "[translate] ✓ Translation complete. Input=%d chars, Output=%d chars.",
            len(state.grounded_answer.answer_text),
            len(translated_text),
        )

        translation = Translation(
            answer_id=state.grounded_answer.id,
            target_language=target_lang,
            translated_text=translated_text,
        )

        event = TranslationCompleted(
            command_id=state.command.id,
            translation_id=translation.id,
            target_language=target_lang,
        )
        state.events.append(event)

        return {"translation": translation}

    async def _node_synthesize(self, state: PipelineState) -> dict:
        """Synthesize audio from the translated text.

        If TTS raises or returns empty bytes, we record a pipeline failure
        rather than emitting a false AudioSynthesized success event.
        """
        if not state.translation:
            return {"audio_response": None}

        logger.info(
            "[synthesize] Synthesizing audio for translation (len=%d chars)...",
            len(state.translation.translated_text),
        )

        try:
            audio_bytes = await self.tts_port.synthesize(
                state.translation.translated_text,
                CAPTAIN_PRESET,
            )
        except Exception as e:
            logger.error(
                "[synthesize] TTS synthesis FAILED — recording pipeline failure. Error: %s", e
            )
            state.fallback_reason = f"TTS synthesis failed: {e}"
            state.status = PipelineStatus.FAILED
            return {"audio_response": None, "status": PipelineStatus.FAILED, "fallback_reason": state.fallback_reason}

        # Double-check: adapter should raise on empty, but guard here too.
        if not audio_bytes:
            msg = "TTS adapter returned empty bytes without raising — treating as failure."
            logger.error("[synthesize] %s", msg)
            state.fallback_reason = msg
            state.status = PipelineStatus.FAILED
            return {"audio_response": None, "status": PipelineStatus.FAILED, "fallback_reason": state.fallback_reason}

        self.audio_dir.mkdir(parents=True, exist_ok=True)
        # Use .mp3 extension — edge-tts produces MP3, not WAV
        audio_path = self.audio_dir / f"{state.command.id}.mp3"
        audio_path.write_bytes(audio_bytes)

        # Rough duration estimate: MP3 at 128kbps → 16000 bytes/sec
        duration_ms = max(int(len(audio_bytes) / 16000 * 1000), 1)

        logger.info(
            "[synthesize] ✓ Audio saved to %s — size=%d bytes, estimated duration=%.1fs.",
            audio_path,
            len(audio_bytes),
            duration_ms / 1000,
        )

        audio_response = AudioResponse(
            translation_id=state.translation.id,
            voice_profile_id=CAPTAIN_PRESET.id,
            audio_path=str(audio_path),
            duration_ms=duration_ms,
        )

        event = AudioSynthesized(
            command_id=state.command.id,
            audio_response_id=audio_response.id,
            voice_profile_id=CAPTAIN_PRESET.id,
            duration_ms=audio_response.duration_ms,
        )
        state.events.append(event)

        event2 = AudioResponseReady(
            command_id=state.command.id,
            audio_response_id=audio_response.id,
        )
        state.events.append(event2)

        return {"audio_response": audio_response}

    async def _node_fallback(self, state: PipelineState) -> dict:
        """Emit a fallback response when the pipeline fails."""
        reason = state.fallback_reason or "Unable to provide a grounded answer"
        state.status = PipelineStatus.UNGROUNDED

        event = PipelineFallback(
            command_id=state.command.id,
            reason=reason,
        )
        state.events.append(event)

        return {"status": PipelineStatus.UNGROUNDED, "fallback_reason": reason}

