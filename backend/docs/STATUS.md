# Backend Status & Readiness

This document outlines the implementation status of the Captain Voice Assistant backend for frontend integration (e.g. Lovable).

---

## 1. Environment Configuration & CORS

- **CORS Allowed Origins**: Configured via the `CORS_ORIGINS` environment variable (comma-separated string or JSON array).
- **Default Origins (local dev)**:
  - `http://localhost:3000`
  - `http://localhost:5173`
  - `http://localhost:8080`
  - `http://127.0.0.1:3000`
  - `http://127.0.0.1:5173`
  - `http://127.0.0.1:8080`
- **Authentication / Role Header**: Passed via `X-User-Role` (`captain`, `crew`, `guest`).
- **Error Response Shape**: All endpoints strictly return `{"detail": "human-readable message"}` on errors (400, 403, 404, 422, 500).

---

## 2. Fully Live API Endpoints

All endpoints documented in `API_REFERENCE.md` are implemented and verified via automated integration tests:

| Method | Endpoint Path | Access Role | Description |
|---|---|---|---|
| `GET` | `/api/v1/health` | Public | System status and version |
| `POST` | `/api/v1/commands` | `captain`, `crew` | Asynchronously submit command & trigger pipeline |
| `GET` | `/api/v1/commands/{command_id}` | `captain`, `crew` | Poll command execution status, citations & audio URL |
| `GET` | `/api/v1/commands/{command_id}/trace` | `captain`, `crew` | Fetch complete pipeline execution trace event log |
| `GET` | `/api/v1/commands/{command_id}/stream` | `captain`, `crew` | Stream live pipeline events via SSE (`text/event-stream`) |
| `GET` | `/api/v1/conversations/{conversation_id}` | `captain`, `crew` | Fetch conversation history and command summary |
| `GET` | `/api/v1/audio/{audio_response_id}` | `captain`, `crew` | Download/stream synthesized audio (`audio/wav` or `audio/mpeg`) |
| `POST` | `/api/v1/knowledge/documents` | `captain` | Direct bulk document seed ingestion into vector store |
| `POST` | `/api/v1/knowledge/submissions` | `captain`, `crew`, `guest` | Submit proposed knowledge; evaluated instantly by Rule Engine |
| `GET` | `/api/v1/knowledge/submissions` | `captain` | List/filter knowledge review queue (`?status=pending`) |
| `GET` | `/api/v1/knowledge/submissions/{submission_id}` | `captain`, submitter | Get single submission details & rule breakdown |
| `POST` | `/api/v1/knowledge/submissions/{submission_id}/approve` | `captain` | Approve submission and index into vector store |
| `POST` | `/api/v1/knowledge/submissions/{submission_id}/reject` | `captain` | Reject submission |

---

## 3. Adapters & Subsystems Status

- **Database**: SQLite async (`sqlite+aiosqlite:///./data/captain.db`) storing conversations, commands, events, knowledge submissions, translations, audio metadata.
- **Vector Store**: ChromaDB local vector store (`./chroma`).
- **LLM Adapter**: Local Ollama adapter (`ollama`) and configurable `FakeLLMAdapter` for testing/fallback.
- **Translator Adapter**: Local Argos Translate adapter (`argos`) and `FakeTranslatorAdapter`.
- **TTS Adapter**: Local Coqui TTS adapter (`coqui`) and `FakeTTSAdapter`.
- **Rule Engine**: Live domain rules (`MinMaxLengthRule`, `BlocklistKeywordRule`, `DuplicateSimilarityRule`, `TrustedRoleAutoApproveRule`).

---

## 4. Scope & Intentionally Deferred Features

- **Multi-Agent (§7 / Step 9)**: Intentionally not started.
- **Frontend Scaffolding (§13 / Step 7)**: Intentionally skipped backend side — the UI is built separately in Lovable and connected via `API_REFERENCE.md`.
