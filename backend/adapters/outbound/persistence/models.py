from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ConversationModel(Base):
    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    captain_id: Mapped[str] = mapped_column(String(128))
    target_language: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    commands: Mapped[list["CommandModel"]] = relationship(back_populates="conversation")


class CommandModel(Base):
    __tablename__ = "commands"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    conversation_id: Mapped[UUID] = mapped_column(ForeignKey("conversations.id"))
    input_text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    conversation: Mapped[ConversationModel] = relationship(back_populates="commands")
    grounded_answer: Mapped["GroundedAnswerModel | None"] = relationship(
        back_populates="command", uselist=False
    )


class KnowledgeDocumentModel(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    title: Mapped[str] = mapped_column(String(512))
    source_path: Mapped[str] = mapped_column(String(1024))

    chunks: Mapped[list["KnowledgeChunkModel"]] = relationship(back_populates="document")


class KnowledgeChunkModel(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("knowledge_documents.id"))
    content: Mapped[str] = mapped_column(Text)

    document: Mapped[KnowledgeDocumentModel] = relationship(back_populates="chunks")


class RetrievedChunkModel(Base):
    __tablename__ = "retrieved_chunks"

    command_id: Mapped[UUID] = mapped_column(ForeignKey("commands.id"), primary_key=True)
    chunk_id: Mapped[UUID] = mapped_column(ForeignKey("knowledge_chunks.id"), primary_key=True)
    similarity_score: Mapped[float] = mapped_column(Float)


class GroundedAnswerModel(Base):
    __tablename__ = "grounded_answers"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    command_id: Mapped[UUID] = mapped_column(ForeignKey("commands.id"), unique=True)
    answer_text: Mapped[str] = mapped_column(Text)
    citations_json: Mapped[str] = mapped_column(Text)

    command: Mapped[CommandModel] = relationship(back_populates="grounded_answer")


class TranslationModel(Base):
    __tablename__ = "translations"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    answer_id: Mapped[UUID] = mapped_column(ForeignKey("grounded_answers.id"))
    target_language: Mapped[str] = mapped_column(String(16))
    translated_text: Mapped[str] = mapped_column(Text)


class AudioResponseModel(Base):
    __tablename__ = "audio_responses"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    translation_id: Mapped[UUID] = mapped_column(ForeignKey("translations.id"))
    voice_profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True))
    audio_path: Mapped[str] = mapped_column(String(1024))
    duration_ms: Mapped[int] = mapped_column(Integer)


class PipelineEventModel(Base):
    __tablename__ = "pipeline_events"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    command_id: Mapped[UUID] = mapped_column(ForeignKey("commands.id"))
    event_type: Mapped[str] = mapped_column(String(128))
    payload_json: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class KnowledgeSubmissionModel(Base):
    __tablename__ = "knowledge_submissions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    submitted_by: Mapped[str] = mapped_column(String(128))
    submitter_role: Mapped[str] = mapped_column(String(32))
    raw_content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32))
    rule_results_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
