# API Reference — Captain Voice Assistant

Companion to `ARCHITECTURE.md`. Covers every endpoint's request body, response body, and which user roles can call it.

---

## User roles

| Role | Who | Can do |
|---|---|---|
| `captain` | The primary operator (owner of the system) | Everything — submit commands, view all history/traces, seed the KB, review and approve/reject knowledge submissions |
| `crew` | Other authenticated users | Submit commands for their own conversations, submit new knowledge (goes to review queue), view their own submissions |
| `guest` | Unauthenticated or low-trust caller | Submit knowledge only (always goes to review, never auto-approved) — no access to commands, conversations, or audio |

Role is passed via an `X-User-Role` header (or resolved from an auth token, if/when real auth is added — see `ARCHITECTURE.md` §3). This is a minimal role model, not full RBAC.

---

## 1. Commands

### `POST /api/v1/commands`
Submit a Captain/Crew text command. Kicks off the RAG → translate → TTS pipeline asynchronously.

**Access:** `captain`, `crew`

**Request body**
```json
{
  "conversation_id": "uuid | null",
  "input_text": "string, required",
  "target_language": "string, ISO 639-1 code, e.g. \"am\" for Amharic"
}
```
`conversation_id` omitted or `null` starts a new conversation.

**Response `202 Accepted`**
```json
{
  "command_id": "uuid",
  "conversation_id": "uuid",
  "status": "pending"
}
```

---

### `GET /api/v1/commands/{command_id}`
Poll for status and final result.

**Access:** `captain`, `crew` (only their own commands)

**Response `200 OK`**
```json
{
  "command_id": "uuid",
  "conversation_id": "uuid",
  "status": "pending | grounded | ungrounded | failed",
  "input_text": "string",
  "answer_text": "string | null",
  "citations": [
    { "chunk_id": "uuid", "document_title": "string", "similarity_score": 0.87 }
  ],
  "translated_text": "string | null",
  "target_language": "string",
  "audio_url": "string | null",
  "created_at": "iso8601",
  "completed_at": "iso8601 | null"
}
```

---

### `GET /api/v1/commands/{command_id}/trace`
Full pipeline event log for this command (retrieval, grounding, translation, synthesis stages).

**Access:** `captain`, `crew` (only their own commands)

**Response `200 OK`**
```json
{
  "command_id": "uuid",
  "events": [
    {
      "event_type": "RetrievalCompleted | AnswerGrounded | TranslationCompleted | AudioSynthesized | PipelineFallback",
      "payload": { "...": "event-specific fields, e.g. chunk ids, retry count, duration_ms" },
      "occurred_at": "iso8601"
    }
  ]
}
```

---

### `GET /api/v1/commands/{command_id}/stream`
Same data as `/trace`, pushed live as `text/event-stream` (SSE) while the pipeline runs.

**Access:** `captain`, `crew` (only their own commands)

**Response:** `Content-Type: text/event-stream`, one event per pipeline stage:
```
event: pipeline_update
data: {"event_type": "RetrievalCompleted", "payload": {...}, "occurred_at": "iso8601"}
```
Stream closes after a terminal event (`AudioSynthesized` or `PipelineFallback`).

---

## 2. Conversations

### `GET /api/v1/conversations/{conversation_id}`
Full history for a conversation.

**Access:** `captain`, `crew` (only their own conversations)

**Response `200 OK`**
```json
{
  "conversation_id": "uuid",
  "captain_id": "string",
  "target_language": "string",
  "created_at": "iso8601",
  "commands": [
    { "command_id": "uuid", "input_text": "string", "status": "string", "created_at": "iso8601" }
  ]
}
```

---

## 3. Audio

### `GET /api/v1/audio/{audio_response_id}`
Streams the synthesized audio file for playback/download.

**Access:** `captain`, `crew` (only audio from their own commands)

**Response `200 OK`**
`Content-Type: audio/mpeg` (or `audio/wav`) — raw audio bytes, no JSON body.

**Response `404 Not Found`** if not yet synthesized or doesn't exist:
```json
{ "detail": "Audio response not found" }
```

---

## 4. Knowledge base — seed ingestion

### `POST /api/v1/knowledge/documents`
Bulk-load initial/trusted documents directly into the knowledge base (bypasses the review workflow — for seeding, not everyday additions).

**Access:** `captain` only

**Request body**
```json
{
  "documents": [
    { "title": "string", "content": "string" }
  ]
}
```

**Response `201 Created`**
```json
{
  "ingested_count": 12,
  "document_ids": ["uuid", "uuid"]
}
```

---

## 5. Knowledge base — submissions (rule-based curation)

### `POST /api/v1/knowledge/submissions`
Propose new information to add to the knowledge base. Runs through the rule engine immediately (see `ARCHITECTURE.md` §10).

**Access:** `captain`, `crew`, `guest` (everyone can submit)

**Request body**
```json
{
  "submitted_by": "string, user id",
  "submitter_role": "captain | crew | guest",
  "raw_content": "string, 20–4000 chars"
}
```

**Response `201 Created`**
```json
{
  "submission_id": "uuid",
  "status": "pending | approved | rejected",
  "rule_results": [
    { "rule": "MinMaxLengthRule", "outcome": "pass" },
    { "rule": "BlocklistKeywordRule", "outcome": "pass" },
    { "rule": "DuplicateSimilarityRule", "outcome": "pass", "similarity": 0.41 },
    { "rule": "TrustedRoleAutoApproveRule", "outcome": "pass" }
  ]
}
```
- `captain` + all rules pass → `status: "approved"`, indexed immediately.
- `crew` + all rules pass → `status: "pending"`, goes to review queue.
- Any hard rule fails (length, blocklist, near-duplicate) → `status: "rejected"`, regardless of role.
- `guest` → always `status: "pending"` even if every rule passes.

---

### `GET /api/v1/knowledge/submissions`
Review queue.

**Access:** `captain` only

**Query params:** `?status=pending` (optional filter — `pending | approved | rejected`)

**Response `200 OK`**
```json
{
  "submissions": [
    {
      "id": "uuid",
      "submitted_by": "string",
      "submitter_role": "crew",
      "raw_content": "string",
      "status": "pending",
      "created_at": "iso8601"
    }
  ]
}
```

---

### `GET /api/v1/knowledge/submissions/{submission_id}`
Status and rule breakdown for one submission.

**Access:** `captain` (any submission), `crew`/`guest` (only their own)

**Response `200 OK`**
```json
{
  "id": "uuid",
  "submitted_by": "string",
  "submitter_role": "string",
  "raw_content": "string",
  "status": "pending | approved | rejected | indexed",
  "rule_results": [ { "rule": "string", "outcome": "pass | fail" } ],
  "reviewed_by": "string | null",
  "created_at": "iso8601"
}
```

---

### `POST /api/v1/knowledge/submissions/{submission_id}/approve`
Approve a pending submission and index it into the vector store.

**Access:** `captain` only

**Request body**
```json
{
  "reviewed_by": "string, captain user id"
}
```

**Response `200 OK`**
```json
{
  "id": "uuid",
  "status": "approved",
  "indexed": true
}
```

---

### `POST /api/v1/knowledge/submissions/{submission_id}/reject`
Reject a pending submission.

**Access:** `captain` only

**Request body**
```json
{
  "reviewed_by": "string, captain user id",
  "reason": "string, optional"
}
```

**Response `200 OK`**
```json
{
  "id": "uuid",
  "status": "rejected",
  "reason": "string | null"
}
```

---

## 6. Health

### `GET /api/v1/health`
**Access:** public, no role required

**Response `200 OK`**
```json
{ "status": "ok", "version": "string" }
```

---

## Error shape (all endpoints)

```json
{ "detail": "human-readable message" }
```
Common status codes: `400` bad input, `403` role not allowed, `404` not found, `422` validation error, `500` internal error.
