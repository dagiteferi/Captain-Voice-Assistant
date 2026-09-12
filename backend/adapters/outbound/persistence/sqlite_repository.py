from __future__ import annotations

import json
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from adapters.outbound.persistence.event_codec import dump_event, load_event
from adapters.outbound.persistence.models import (
    AudioResponseModel,
    CommandModel,
    ConversationModel,
    GroundedAnswerModel,
    PipelineEventModel,
    TranslationModel,
)
from domain.conversation.entities import Command, Conversation, GroundedAnswer
from domain.conversation.value_objects import Citation, CommandStatus, Language
from domain.events import DomainEvent
from domain.voice.entities import AudioResponse, Translation


class SQLiteConversationRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def save_conversation(self, conversation: Conversation) -> None:
        async with self._session_factory() as session:
            async with session.begin():
                row = await session.get(ConversationModel, conversation.id)
                if row is None:
                    session.add(
                        ConversationModel(
                            id=conversation.id,
                            captain_id=conversation.captain_id,
                            target_language=conversation.target_language.code,
                            created_at=conversation.created_at,
                        )
                    )
                    return
                row.captain_id = conversation.captain_id
                row.target_language = conversation.target_language.code

    async def get_conversation(self, conversation_id: UUID) -> Conversation | None:
        async with self._session_factory() as session:
            row = await session.get(
                ConversationModel,
                conversation_id,
                options=(selectinload(ConversationModel.commands).selectinload(CommandModel.grounded_answer),),
            )
            if row is None:
                return None
            conversation = Conversation(
                id=row.id,
                captain_id=row.captain_id,
                target_language=Language(row.target_language),
                created_at=row.created_at,
            )
            conversation.commands = [_command_from_row(item) for item in row.commands]
            return conversation

    async def save_command(self, command: Command) -> None:
        async with self._session_factory() as session:
            async with session.begin():
                row = await session.get(CommandModel, command.id)
                if row is None:
                    session.add(
                        CommandModel(
                            id=command.id,
                            conversation_id=command.conversation_id,
                            input_text=command.input_text,
                            status=command.status.value,
                            voice_id=command.voice_id,
                            created_at=command.created_at,
                        )
                    )
                    return
                row.input_text = command.input_text
                row.status = command.status.value
                row.voice_id = command.voice_id

    async def get_command(self, command_id: UUID) -> Command | None:
        async with self._session_factory() as session:
            row = await session.get(
                CommandModel,
                command_id,
                options=(selectinload(CommandModel.grounded_answer),),
            )
            if row is None:
                return None
            return _command_from_row(row)

    async def save_grounded_answer(self, answer: GroundedAnswer) -> None:
        answer.validate()
        payload = json.dumps(
            [
                {
                    "chunk_id": str(citation.chunk_id),
                    "document_id": str(citation.document_id) if citation.document_id else None,
                    "snippet": citation.snippet,
                }
                for citation in answer.citations
            ]
        )
        async with self._session_factory() as session:
            async with session.begin():
                row = await session.get(GroundedAnswerModel, answer.id)
                if row is None:
                    session.add(
                        GroundedAnswerModel(
                            id=answer.id,
                            command_id=answer.command_id,
                            answer_text=answer.answer_text,
                            citations_json=payload,
                        )
                    )
                    return
                row.answer_text = answer.answer_text
                row.citations_json = payload

    async def save_translation(self, translation: Translation) -> None:
        async with self._session_factory() as session:
            async with session.begin():
                existing = (
                    await session.scalars(
                        select(TranslationModel).where(
                            TranslationModel.answer_id == translation.answer_id
                        )
                    )
                ).first()
                if existing is None:
                    session.add(
                        TranslationModel(
                            id=translation.id,
                            answer_id=translation.answer_id,
                            target_language=translation.target_language.code,
                            translated_text=translation.translated_text,
                        )
                    )
                    return
                existing.translated_text = translation.translated_text
                existing.target_language = translation.target_language.code
                translation.id = existing.id

    async def save_audio_response(self, audio: AudioResponse) -> None:
        async with self._session_factory() as session:
            async with session.begin():
                row = await session.get(AudioResponseModel, audio.id)
                if row is None:
                    session.add(
                        AudioResponseModel(
                            id=audio.id,
                            translation_id=audio.translation_id,
                            voice_profile_id=audio.voice_profile_id,
                            audio_path=audio.audio_path,
                            duration_ms=audio.duration_ms,
                        )
                    )
                    return
                row.audio_path = audio.audio_path
                row.duration_ms = audio.duration_ms
                row.voice_profile_id = audio.voice_profile_id

    async def get_translation_for_answer(self, answer_id: UUID) -> Translation | None:
        async with self._session_factory() as session:
            row = (
                await session.scalars(
                    select(TranslationModel).where(TranslationModel.answer_id == answer_id)
                )
            ).first()
            if row is None:
                return None
            return Translation(
                id=row.id,
                answer_id=row.answer_id,
                target_language=Language(row.target_language),
                translated_text=row.translated_text,
            )

    async def get_audio_for_translation(self, translation_id: UUID) -> AudioResponse | None:
        async with self._session_factory() as session:
            row = (
                await session.scalars(
                    select(AudioResponseModel).where(
                        AudioResponseModel.translation_id == translation_id
                    )
                )
            ).first()
            if row is None:
                return None
            return _audio_from_row(row)

    async def get_audio_response(self, audio_id: UUID) -> AudioResponse | None:
        async with self._session_factory() as session:
            row = await session.get(AudioResponseModel, audio_id)
            if row is None:
                return None
            return _audio_from_row(row)

    async def append_event(self, command_id: UUID, event: DomainEvent) -> None:
        event_type, payload_json = dump_event(event)
        async with self._session_factory() as session:
            async with session.begin():
                session.add(
                    PipelineEventModel(
                        id=uuid4(),
                        command_id=command_id,
                        event_type=event_type,
                        payload_json=payload_json,
                        occurred_at=event.occurred_at,
                    )
                )

    async def list_events(self, command_id: UUID) -> list[DomainEvent]:
        async with self._session_factory() as session:
            result = await session.scalars(
                select(PipelineEventModel)
                .where(PipelineEventModel.command_id == command_id)
                .order_by(PipelineEventModel.occurred_at, PipelineEventModel.id)
            )
            return [
                load_event(row.event_type, row.payload_json, row.occurred_at)
                for row in result
            ]

    async def list_events_with_ids(self, command_id: UUID, since_event_id: UUID | None = None) -> list[dict]:
        """Return pipeline events as rows with id, event_type, payload_json, occurred_at.

        If `since_event_id` is provided, only return events that occurred strictly
        after that event (by occurred_at, with id as tiebreaker).
        """
        async with self._session_factory() as session:
            base = select(PipelineEventModel).where(PipelineEventModel.command_id == command_id)

            if since_event_id is not None:
                since_row = await session.get(PipelineEventModel, since_event_id)
                if since_row is not None:
                    # only return events with occurred_at > since.occurred_at OR
                    # occurred_at == since.occurred_at AND id > since_id
                    base = base.where(
                        (PipelineEventModel.occurred_at > since_row.occurred_at)
                        | (
                            (PipelineEventModel.occurred_at == since_row.occurred_at)
                            & (PipelineEventModel.id > since_event_id)
                        )
                    )

            result = await session.scalars(base.order_by(PipelineEventModel.occurred_at, PipelineEventModel.id))
            rows = []
            for row in result:
                rows.append(
                    {
                        "id": row.id,
                        "event_type": row.event_type,
                        "payload_json": row.payload_json,
                        "occurred_at": row.occurred_at,
                    }
                )
            return rows

    async def save_submission(self, submission) -> None:
        from domain.knowledge.entities import KnowledgeSubmission
        from adapters.outbound.persistence.models import KnowledgeSubmissionModel
        
        payload = json.dumps(submission.rule_results)
        async with self._session_factory() as session:
            async with session.begin():
                row = await session.get(KnowledgeSubmissionModel, submission.id)
                if row is None:
                    session.add(
                        KnowledgeSubmissionModel(
                            id=submission.id,
                            submitted_by=submission.submitted_by,
                            submitter_role=submission.submitter_role.value,
                            raw_content=submission.raw_content,
                            status=submission.status.value,
                            rule_results_json=payload,
                            created_at=submission.created_at,
                            reviewed_by=submission.reviewed_by,
                        )
                    )
                    return
                row.raw_content = submission.raw_content
                row.status = submission.status.value
                row.reviewed_by = submission.reviewed_by
                row.rule_results_json = payload

    async def get_submission(self, submission_id: UUID):
        from domain.knowledge.value_objects import SubmitterRole, SubmissionStatus
        from domain.knowledge.entities import KnowledgeSubmission
        from adapters.outbound.persistence.models import KnowledgeSubmissionModel
        
        async with self._session_factory() as session:
            row = await session.get(KnowledgeSubmissionModel, submission_id)
            if row is None:
                return None
            rule_results = json.loads(row.rule_results_json) if row.rule_results_json else []
            return KnowledgeSubmission(
                id=row.id,
                submitted_by=row.submitted_by,
                submitter_role=SubmitterRole(row.submitter_role),
                raw_content=row.raw_content,
                status=SubmissionStatus(row.status),
                rule_results=rule_results,
                created_at=row.created_at,
                reviewed_by=row.reviewed_by,
            )

    async def list_submissions(self, status: str | None = None) -> list:
        from domain.knowledge.value_objects import SubmitterRole, SubmissionStatus
        from domain.knowledge.entities import KnowledgeSubmission
        from adapters.outbound.persistence.models import KnowledgeSubmissionModel
        
        async with self._session_factory() as session:
            base = select(KnowledgeSubmissionModel)
            if status is not None:
                base = base.where(KnowledgeSubmissionModel.status == status)
            base = base.order_by(KnowledgeSubmissionModel.created_at.desc())
            result = await session.scalars(base)
            submissions = []
            for row in result:
                rule_results = json.loads(row.rule_results_json) if row.rule_results_json else []
                submissions.append(
                    KnowledgeSubmission(
                        id=row.id,
                        submitted_by=row.submitted_by,
                        submitter_role=SubmitterRole(row.submitter_role),
                        raw_content=row.raw_content,
                        status=SubmissionStatus(row.status),
                        rule_results=rule_results,
                        created_at=row.created_at,
                        reviewed_by=row.reviewed_by,
                    )
                )
            return submissions

    async def delete_all_submissions(self) -> None:
        from adapters.outbound.persistence.models import KnowledgeSubmissionModel

        async with self._session_factory() as session:
            async with session.begin():
                await session.execute(delete(KnowledgeSubmissionModel))

    async def list_document_titles(self) -> list[str]:
        from adapters.outbound.persistence.models import KnowledgeDocumentModel
        async with self._session_factory() as session:
            result = await session.scalars(select(KnowledgeDocumentModel.title))
            return list(result)

    async def list_recent_commands(self, limit: int = 10) -> list:
        from adapters.outbound.persistence.models import CommandModel
        async with self._session_factory() as session:
            result = await session.scalars(
                select(CommandModel).order_by(CommandModel.created_at.desc()).limit(limit)
            )
            return [_command_from_row(r) for r in result]



def _command_from_row(row: CommandModel) -> Command:
    command = Command(
        id=row.id,
        conversation_id=row.conversation_id,
        input_text=row.input_text,
        status=CommandStatus(row.status),
        voice_id=getattr(row, "voice_id", None),
        created_at=row.created_at,
    )
    if row.grounded_answer is not None:
        command.grounded_answer = _answer_from_row(row.grounded_answer)
    return command


def _answer_from_row(row: GroundedAnswerModel) -> GroundedAnswer:
    raw = json.loads(row.citations_json)
    citations = [
        Citation(
            chunk_id=UUID(item["chunk_id"]),
            document_id=UUID(item["document_id"]) if item.get("document_id") else None,
            snippet=item.get("snippet"),
        )
        for item in raw
    ]
    return GroundedAnswer(
        id=row.id,
        command_id=row.command_id,
        answer_text=row.answer_text,
        citations=citations,
    )


def _audio_from_row(row: AudioResponseModel) -> AudioResponse:
    return AudioResponse(
        id=row.id,
        translation_id=row.translation_id,
        voice_profile_id=row.voice_profile_id,
        audio_path=row.audio_path,
        duration_ms=row.duration_ms,
    )
