# Captain Voice Assistant

<p align="center">
  <strong>RAG-Based Voice Assistant with Translation Pipeline</strong>
</p>

<p align="center">
  A Captain inputs text commands → the system retrieves context from a knowledge base (RAG) →
  generates a grounded response → translates it → converts to speech using a consistent voice profile.
</p>

---

## Architecture

```text
┌──────────────────────┐              ┌──────────────────────────────────────────┐
│  Frontend (Vite)     │   HTTP/JSON  │  Backend (FastAPI)                       │
│  React · Tailwind    │ ────────────►│  Hexagonal architecture                  │
│  TypeScript          │              │  domain → ports → adapters               │
│                      │              │                                          │
│  • Command Console   │              │  ┌─────────────────────────────────────┐  │
│  • Pipeline Trace    │              │  │  LangGraph Orchestration Pipeline   │  │
│  • Submit Knowledge  │              │  │                                     │  │
│  • Review Queue      │              │  │  retrieve → grade → generate →      │  │
│                      │              │  │  verify → translate → synthesize    │  │
└──────────────────────┘              │  └─────────────────────────────────────┘  │
                                      │                                          │
                                      │  Adapters (all API-based, no local      │
                                      │  model downloads):                      │
                                      │  • Gemini 2.0 Flash (LLM)              │
                                      │  • Gemini text-embedding-004            │
                                      │  • MyMemory (translation, free)        │
                                      │  • Google Cloud TTS (speech)           │
                                      │  • ChromaDB (local vector store)       │
                                      │  • SQLite (persistence)               │
                                      └──────────────────────────────────────────┘
```

### Pipeline Flow

```text
User Command (text)
  │
  ▼
┌─────────┐    ┌───────────┐    ┌──────────┐    ┌──────────┐    ┌───────────┐    ┌────────────┐
│ Retrieve │───►│ Grade Docs│───►│ Generate │───►│  Verify  │───►│ Translate │───►│ Synthesize │
│ (Chroma) │    │  (Gemini) │    │ (Gemini) │    │ Grounding│    │(MyMemory) │    │(Google TTS)│
└─────────┘    └───────────┘    └──────────┘    └──────────┘    └───────────┘    └────────────┘
                                                                                       │
                                                                                       ▼
                                                                              Audio Response (MP3)
```

---

## Tech Stack

| Layer | Technology | Cost |
|-------|------------|------|
| **LLM** | Google Gemini 2.0 Flash | Free tier (15 RPM) |
| **Embeddings** | Gemini text-embedding-004 | Free tier |
| **Translation** | MyMemory API | Free (1000 req/day) |
| **TTS** | Google Cloud Text-to-Speech | Free tier (1M chars/month) |
| **Vector Store** | ChromaDB | Local, free |
| **Database** | SQLite | Local, free |
| **Backend** | FastAPI + LangGraph | — |
| **Frontend** | React + Vite + Tailwind | — |

**Why these choices:**
- **Gemini**: Free tier is generous, excellent quality, same key for LLM + embeddings.
- **MyMemory**: Completely free, no signup needed, supports English↔Amharic.
- **Google Cloud TTS**: Free tier covers demo usage, excellent voice quality with Neural2 voices.
- **No local model downloads**: All AI is API-based via `httpx` — fast startup, no GPU needed.

---

## Prerequisites

| Requirement | How to get it |
|-------------|---------------|
| Python **3.11+** | https://python.org |
| Node.js **18+** | https://nodejs.org |
| **Gemini API key** | https://ai.google.dev/ (free) |
| **Google Cloud TTS API key** | [Cloud Console](https://console.cloud.google.com/apis/library/texttospeech.googleapis.com) |

---

## Quick Start

### 1. Clone & Setup Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Configure `.env`

```bash
cp ../.env.example .env
# Edit .env — add your API keys:
#   GEMINI_API_KEY=your-key-here
#   GOOGLE_TTS_API_KEY=your-key-here
```

### 3. Start Backend

```bash
fastapi dev main.py
```

You should see:
```
=== Captain Voice Assistant startup ===
Stack: Gemini LLM + Gemini Embeddings + MyMemory Translate + Google TTS
[startup] Database ready.
[startup] All components ready. Serving requests.
```

### 4. Seed Knowledge Base

In a separate terminal (with backend running):

```bash
python tools/seed_knowledge.py
```

This replaces any previous sample KB with profile documents from Dagmawi Teferi's CV.

Output:
```
✓ Successfully ingested 21 documents!
```

### 5. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 → type a command → get a grounded, translated voice response.

---

## Environment Variables

### Backend (`.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | **Yes** | — | Google AI Studio API key |
| `GEMINI_MODEL` | No | `gemini-2.0-flash` | Gemini model name |
| `GOOGLE_TTS_API_KEY` | **Yes** | — | Google Cloud TTS API key |
| `GOOGLE_TTS_VOICE_EN` | No | `en-US-Neural2-D` | English voice name |
| `GOOGLE_TTS_VOICE_AM` | No | `am-ET-Standard-A` | Amharic voice name |
| `MYMEMORY_EMAIL` | No | — | Optional: increases daily limit to 10,000 |
| `SQLITE_URL` | No | `sqlite+aiosqlite:///./data/captain.db` | Database path |
| `CHROMA_DIR` | No | `./chroma` | Vector store directory |
| `AUDIO_DIR` | No | `./data/audio` | Synthesized audio output |
| `CORS_ORIGINS` | No | `http://localhost:5173,...` | Frontend origins |
| `LOG_LEVEL` | No | `INFO` | Logging level |

### Frontend (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend URL |
| `VITE_DEFAULT_LANGUAGE` | `am` | Default target language |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/health` | Health check + stack info |
| `POST` | `/api/v1/commands` | Submit a command (starts pipeline) |
| `GET` | `/api/v1/commands/{id}` | Get command result |
| `GET` | `/api/v1/commands/{id}/trace` | Get pipeline trace events |
| `GET` | `/api/v1/commands/{id}/stream` | SSE stream of trace events |
| `POST` | `/api/v1/knowledge/documents` | Bulk ingest KB documents |
| `POST` | `/api/v1/knowledge/submissions` | Submit new knowledge |
| `GET` | `/api/v1/knowledge/submissions` | List submissions (review queue) |
| `POST` | `/api/v1/knowledge/submissions/{id}/approve` | Approve submission |
| `POST` | `/api/v1/knowledge/submissions/{id}/reject` | Reject submission |
| `GET` | `/api/v1/audio/{id}` | Stream synthesized audio |

---

## TTS Voice Tradeoff

This project uses **Google Cloud TTS Neural2 voices** rather than true voice cloning
(e.g. ElevenLabs, Coqui XTTS).

**Tradeoff:** A consistent, high-quality neural voice (`en-US-Neural2-D` for English,
`am-ET-Standard-A` for Amharic) is used for all responses rather than a cloned
Captain-specific voice. As the assignment notes: *"If true voice cloning isn't feasible
in the time given, a well-configured single consistent voice profile is acceptable —
explain the tradeoff in your README."*

The pipeline architecture supports swapping in a real voice-cloning adapter at the
`TTSPort` interface without changing any other code.

---

## Known Limitations

1. **MyMemory translation** has a 1000 req/day free limit (10,000 with email).
2. **Google TTS** free tier is 1M characters/month — fine for demo, not production.
3. **Gemini free tier** is 15 RPM — sufficient for demo, rate-limit for concurrent users.
4. **No voice cloning** — uses consistent Neural2 profile (see tradeoff above).
5. **ChromaDB** is an embedded vector store — for production, use a hosted solution.

## What I'd Improve With More Time

1. Add WebSocket/SSE for real-time pipeline progress (partial implementation exists).
2. Implement true voice cloning with ElevenLabs API.
3. Add user authentication (JWT).
4. Deploy backend to Hugging Face Spaces, frontend to Vercel.
5. Add comprehensive test coverage for all pipeline nodes.
6. Implement conversation memory / multi-turn context.

---

## Project Structure

```text
captain-voice-assistant/
├── .env.example                    # All env vars documented
├── backend/
│   ├── main.py                     # FastAPI entrypoint
│   ├── config/
│   │   ├── settings.py             # Pydantic Settings (reads .env)
│   │   └── di_container.py         # Dependency injection wiring
│   ├── domain/                     # Entities, value objects, events
│   ├── application/                # Commands, queries, ports
│   ├── adapters/
│   │   ├── inbound/api/routers/    # FastAPI route handlers
│   │   └── outbound/
│   │       ├── llm/gemini_adapter.py
│   │       ├── vector_store/gemini_embedder.py
│   │       ├── translation/mymemory_adapter.py
│   │       ├── tts/google_tts_adapter.py
│   │       ├── persistence/        # SQLite repository
│   │       └── orchestration/      # LangGraph pipeline
│   ├── tools/seed_knowledge.py     # KB seeder script
│   └── pyproject.toml
└── frontend/
    ├── src/
    │   ├── pages/                  # Console, Trace, Knowledge, Review
    │   ├── features/               # Audio player, etc.
    │   └── shared/                 # API client, roles, UI components
    └── package.json
```

---

## Author

**Dagmawi Teferi**

Built for the Captain Voice Assistant technical assignment.
