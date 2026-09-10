# Captain Voice Assistant — Solution Architecture

**Style:** Domain-Driven Design (DDD) + Hexagonal Architecture (Ports & Adapters) + CQRS + Event-Driven orchestration
**Orchestration engine:** LangGraph (stateful graph, not a linear chain)
**Backend:** FastAPI (async)
**Persistence:** SQLite via SQLAlchemy 2.0 (async) behind a repository port — swappable for Postgres later
**Frontend:** React + TypeScript, Feature-Sliced Design (FSD), WebSocket/SSE streaming

---

## 1. Why this combination (and not something else)

| Concern | Choice | Reasoning |
|---|---|---|
| Domain complexity | **DDD** | The pipeline has real domain concepts (Command, KnowledgeChunk, GroundedAnswer, Translation, VoiceProfile, AudioResponse) with invariants ("no response without at least one citation", "no TTS without a resolved voice profile"). Worth modeling explicitly rather than as a script. |
| Framework coupling | **Hexagonal (Ports & Adapters)** | LLM vendor, vector store, TTS vendor, and translation vendor are all things you *will* swap (cost, quality, latency). Hexagonal keeps the domain ignorant of LangChain/LangGraph/ElevenLabs/FAISS specifics — they're adapters behind ports. |
| Orchestration of a multi-step, stateful, occasionally-branching pipeline | **LangGraph** | This isn't a single LLM call — it's Retrieve → Grade → Generate → (retry if ungrounded) → Translate → Synthesize. That's a state machine with conditional edges, which is exactly what LangGraph models (vs. a linear LCEL chain that can't easily retry/branch). |
| Read vs write asymmetry | **CQRS (light)** | Writes = submitting a Captain command (mutates conversation state, triggers pipeline). Reads = fetching history, pipeline trace, audio artifacts. Separating them lets the read side be simple SQL projections while the write side stays behind the domain/use-case layer. |
| Cross-cutting pipeline visibility | **Event-Driven internals** | Every pipeline stage (`RetrievalCompleted`, `AnswerGrounded`, `TranslationCompleted`, `AudioSynthesized`) is published as a domain event. This gives you the required **full pipeline trace** for free, decouples logging/metrics from business logic, and lets the frontend subscribe to progress via SSE without polling. |
| Frontend structure | **Feature-Sliced Design** | Keeps "command-console", "pipeline-trace", "audio-player" as independent verticals instead of a `components/`, `hooks/`, `utils/` soup — mirrors the backend's bounded contexts so a reviewer can map FE feature ↔ BE bounded context. |

This is deliberately **more architecture than the assignment strictly needs** for a 10–50 doc knowledge base — that's fine for a senior-engineer submission where "system design" and "judgment under ambiguity" are graded criteria; the README should say explicitly that you chose to over-invest in structure because the brief asked for "latest architecture / design patterns," and note where you'd simplify for a real MVP.

---

## 2. Free / Local Stack (zero-cost demo)

The ports stay exactly as designed — that's the point of hexagonal architecture. Only the **adapters** change to fully free, local, no-API-key options. Nothing below costs money or needs a credit card.

| Port | Paid option (mentioned earlier) | **Free adapter used for the demo** | Notes |
|---|---|---|---|
| `LLMPort` | Claude / GPT-4 API | **Ollama** running a local model (`llama3.1:8b` or `qwen2.5:7b`) | Runs on CPU or modest GPU; swap model name in config, zero API cost |
| `VectorStorePort` | Pinecone | **Chroma** (local, file-based, embedded) | No server to run — persists to a local folder, ships inside the repo |
| Embeddings | OpenAI embeddings | **sentence-transformers** (`all-MiniLM-L6-v2`) | Runs locally, small (~80MB), fast on CPU |
| `TranslatorPort` | Google Translate / DeepL API | **Argos Translate** (offline, open-source) — fallback: local Ollama model doing translation as a prompt | Argos ships language packs locally, no network call at inference time |
| `TTSPort` | ElevenLabs (paid voice cloning) | **Coqui TTS** (open-source, local) with a single fixed "Captain" voice preset, or **edge-tts** (free, uses Microsoft's public endpoint, no key required) as a lighter fallback | State plainly in the README: true voice *cloning* is the one place a free option is weakest — a consistent preset voice is the honest, explicitly-scoped substitute |
| Persistence | — | **SQLite** (already free/local, unchanged) | |

This means the entire system **runs on a laptop with no API keys, no billing, and no network dependency at inference time** (translation and TTS packs are downloaded once, then run offline). That's worth stating explicitly in the README as a design decision, not just a cost-saving hack — it also makes the demo reproducible for a grader with zero setup friction beyond `pip install`.

> **Composition root benefit, made concrete:** because every one of these is swapped in behind a `Protocol` port, moving from the free stack to the paid stack later (e.g., real ElevenLabs cloning) is a one-line change in `di_container.py` — no domain, application, or API code changes. This is the single best way to *demonstrate* hexagonal architecture in a review: show the free adapter today, point at the interface, and say "this is where Anthropic/ElevenLabs would plug in."

---

## 3. Right-sizing: what we deliberately did NOT build

The patterns below (DDD, hexagonal, CQRS, event-driven, multi-agent) are shown because the brief asked for "latest architecture and design patterns" — but a senior engineer's judgment is knowing where to stop. For this assignment's actual scope (10–50 documents, single user, a few days), the following are **explicitly out of scope**, and the README should say so directly rather than leaving a reviewer to wonder if it was an oversight:

| Not built | Why it would be over-engineering here |
|---|---|
| Separate read/write databases for CQRS | One SQLite file is fine at this scale; CQRS here means separate *code paths*, not infrastructure (see §8) |
| Message broker (Kafka/RabbitMQ) for domain events | An in-process event bus (a list of subscribers) satisfies the trace/logging requirement fully; a broker adds ops overhead with zero benefit at single-process scale |
| Multi-agent supervisor as the *only* implementation | Ship the flat LangGraph pipeline (§6) as the working demo; the multi-agent version (§7) is documented and structurally prepared for (same port, swappable adapter) but only build it out if time allows — don't let it block a working submission |
| Microservices / separate deployable services per bounded context | Bounded contexts are Python packages in one process, not network-separated services — separating them now would add deployment complexity with no team-scaling need yet |
| Kubernetes / containorchestration | A single `docker run` (or even just `uvicorn`) is enough for a demo; a Dockerfile is worth including, a Helm chart is not |
| Auth/multi-tenancy | Single "Captain" as primary operator, but Section 10 needs *some* notion of "other users" for knowledge submission — solved with a minimal `submitter_role` string (`captain`/`crew`/`guest`), not a full auth/permissions system. A stub `captain_id` field elsewhere is enough to show where real auth would extend. |
| ML-based content moderation for new knowledge | A trained classifier or LLM-as-judge would cost money/add latency and non-determinism for a task that ordered free predicate rules (Section 10) solve deterministically and explainably at this scale |

Stating this list in the README does more for a "judgment under ambiguity" score than building any one of these items would — it shows you know the difference between "could add" and "should add now."

---

## 4. Bounded Contexts

```
┌─────────────────────────────────────────────────────────────────┐
│                        Captain Assistant                        │
│                                                                   │
│  ┌───────────────┐   ┌────────────────┐   ┌──────────────────┐  │
│  │  Conversation  │   │   Knowledge     │   │  Voice Delivery  │  │
│  │  (core domain) │   │  (supporting)   │   │   (supporting)   │  │
│  │                │   │                 │   │                  │  │
│  │ Command        │   │ Document        │   │ VoiceProfile     │  │
│  │ GroundedAnswer │   │ Chunk           │   │ Translation      │  │
│  │ PipelineTrace  │   │ RetrievalResult │   │ AudioResponse    │  │
│  │                │   │ KnowledgeSubmis-│   │                  │  │
│  │                │   │ sion (§10)      │   │                  │  │
│  └───────┬────────┘   └────────┬────────┘   └────────┬─────────┘  │
│          │                     │                       │          │
│          └──────────── Domain Events Bus ──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

- **Conversation** (core domain — this is what differentiates the product): owns the Captain's command lifecycle and the invariant "an answer must carry citations to retrieved chunks or it is rejected as ungrounded."
- **Knowledge** (supporting domain): ingestion, chunking, embedding, retrieval — **and now also curation**: `KnowledgeSubmission` is a separate aggregate from `Document`/`Chunk` inside this same context, so new incoming info from any user goes through rule-based review (Section 10) before it ever touches the retrievable knowledge base. Could be extracted into its own service later.
- **Voice Delivery** (supporting domain): translation + TTS. Two ports, two adapters, one aggregate (`AudioResponse`) tying them together.

---

## 5. Hexagonal Layout (Backend)

```
                         ┌────────────────────────────┐
                         │   Inbound Adapters (driving)│
                         │  FastAPI routers, WS/SSE    │
                         └──────────────┬─────────────┘
                                        │ calls
                         ┌──────────────▼─────────────┐
                         │      Application Layer      │
                         │  Use Cases / Command & Query│
                         │  Handlers (CQRS)             │
                         │  - SubmitCommandHandler       │
                         │  - GetHistoryQueryHandler      │
                         └──────────────┬─────────────┘
                                        │ orchestrates
                         ┌──────────────▼─────────────┐
                         │        Domain Layer          │
                         │  Entities, Value Objects,     │
                         │  Aggregates, Domain Events,   │
                         │  Domain Services (pure logic) │
                         │  ── depends on nothing below ─│
                         └──────────────┬─────────────┘
                                        │ defines
                         ┌──────────────▼─────────────┐
                         │           Ports              │
                         │ (interfaces / Protocols)      │
                         │ VectorStorePort, LLMPort,      │
                         │ TranslatorPort, TTSPort,       │
                         │ ConversationRepositoryPort,    │
                         │ EventPublisherPort              │
                         └──────────────┬─────────────┘
                                        │ implemented by
                         ┌──────────────▼─────────────┐
                         │   Outbound Adapters (driven) │
                         │ - LangGraphPipelineAdapter    │
                         │   (implements orchestration   │
                         │    using LLMPort/VectorPort)   │
                         │ - ChromaVectorStoreAdapter      │  (free, local)
                         │ - OllamaLLMAdapter              │  (free, local — §2)
                         │ - ArgosTranslateAdapter         │  (free, offline — §2)
                         │ - CoquiTTSAdapter /             │  (free, local — §2)
                         │   EdgeTTSAdapter                 │
                         │   [paid: AnthropicLLMAdapter,    │
                         │    ElevenLabsTTSAdapter — same    │
                         │    port, swap in di_container.py]│
                         │ - SQLiteConversationRepo         │
                         │   (SQLAlchemy async)             │
                         │ - InMemoryEventBus /              │
                         │   SSEEventPublisher                │
                         └────────────────────────────┘
```

**Dependency rule:** arrows point inward only. Domain layer imports nothing from adapters. LangGraph, SQLAlchemy, ElevenLabs SDK, etc. are all adapter-layer details — the domain talks only to `Protocol`-typed ports.

---

## 6. Where LangGraph fits (important nuance)

LangGraph is **not** the application layer and **not** the domain layer — it is the internal implementation of **one outbound adapter**: `PipelineOrchestratorPort`. This matters because it means:

> **Note:** the flat graph shown below is the simplest valid implementation of that adapter. Section 7 upgrades it to a **multi-agent supervisor** design — same port, same domain, more capable internals. Read this section first for the baseline mental model, then Section 7 for the pattern you'll actually implement.

- Swapping LangGraph for a hand-rolled state machine, or for a different orchestrator, never touches the domain or the FastAPI routes.
- The domain still owns the *rules* (e.g., "an answer without ≥1 grounding citation is invalid" lives in a domain service/value object `GroundedAnswer.validate()`), while LangGraph owns the *execution* (retry loops, conditional branching, streaming).

### LangGraph state graph

```
        ┌─────────────┐
        │  START       │
        └──────┬──────┘
               │
        ┌──────▼──────┐
        │  retrieve    │  → VectorStorePort.search(query)
        └──────┬──────┘
               │
        ┌──────▼──────┐
        │  grade_docs  │  → LLM relevance check on retrieved chunks
        └──────┬──────┘
     no-relevant-docs │ has-relevant-docs
        ┌──────▼──────┐        ┌──────────────┐
        │ fallback_msg │        │   generate    │  → LLMPort.generate(query, chunks)
        └──────┬──────┘        └───────┬──────┘
               │                       │
               │                ┌──────▼──────┐
               │                │ verify_ground │  → citations present? else loop→generate (max 2 retries)
               │                └───────┬──────┘
               │                        │
               └───────────┬────────────┘
                            │
                     ┌──────▼──────┐
                     │  translate   │  → TranslatorPort.translate(text, target_lang)
                     └──────┬──────┘
                            │
                     ┌──────▼──────┐
                     │  synthesize  │  → TTSPort.synthesize(text, voice_profile)
                     └──────┬──────┘
                            │
                     ┌──────▼──────┐
                     │    END       │  → emits AudioResponseReady event
                     └─────────────┘
```

Each node emits a domain event on completion (`RetrievalCompleted`, `AnswerGrounded`, `TranslationCompleted`, `AudioSynthesized`) which is what populates the **pipeline trace** the assignment requires, and what the frontend subscribes to over SSE for live progress.

Treat this section as the fallback design if multi-agent proves too much for the timeline — it satisfies every grading criterion on its own. Section 7 is the upgrade.

---

## 7. Multi-Agent Design (Orchestrator + Specialist Agents)

Rather than one LangGraph pipeline hard-coding every step, model each stage as an **independent agent with a narrow responsibility and its own tools**, coordinated by a single **Orchestrator Agent**. This still lives entirely inside the `PipelineOrchestratorPort` adapter — the domain and application layers don't know or care whether the port is implemented by one graph or five agents.

### 7.1 Why multi-agent here (and not just more graph nodes)

A plain node is "run this function." An **agent** is appropriate when a step needs to *reason and decide*, not just transform data — e.g., deciding whether retrieved chunks are actually relevant, deciding to re-query with a reformulated question, or deciding which of several TTS providers to fall back to on failure. Where a step is a pure deterministic transform (e.g., "call the translation API"), keep it a plain tool call inside an agent rather than inventing an agent for it — don't multi-agent things that don't need judgment.

### 7.2 Agent roster

| Agent | Responsibility | Tools it owns | Reports to |
|---|---|---|---|
| **Orchestrator Agent** | Owns the overall task state machine; decides which specialist to invoke next, when to retry, when to give up and fall back | delegate_to(agent), get_pipeline_state | — (top-level) |
| **Retrieval Agent** | Formulates/reformulates the query, calls the vector store, judges whether results are relevant enough | `VectorStorePort.search`, query-rewrite tool | Orchestrator |
| **Grounding/Generation Agent** | Generates the answer strictly from retrieved chunks; self-checks that every claim traces to a citation; requests re-retrieval if it can't ground a claim | `LLMPort.generate`, citation-checker tool | Orchestrator |
| **Translation Agent** | Translates the grounded answer, preserving citation markers/terminology consistency | `TranslatorPort.translate`, glossary/terminology lookup | Orchestrator |
| **Voice Synthesis Agent** | Selects the voice profile, calls TTS, retries/falls back to a secondary provider or a non-cloned voice on failure | `TTSPort.synthesize`, voice-profile resolver | Orchestrator |

Each specialist agent is scoped to **one port** (or a small tool set derived from one port) — this preserves the hexagonal boundary. The Orchestrator itself talks to no external system directly; it only delegates.

### 7.3 Orchestrator as a supervisor graph (LangGraph)

LangGraph's role changes slightly from Section 6: instead of one flat graph of function nodes, the **Orchestrator is the graph**, and each node's "work" is delegated to a sub-agent (itself optionally a small LangGraph ReAct loop, or a direct tool-calling LLM call). This is the standard **supervisor pattern**.

```
                         ┌─────────────────────────────┐
                         │      Orchestrator Agent       │
                         │  (supervisor / router node)   │
                         └──────────────┬───────────────┘
              decides next specialist   │
        ┌────────────────┬──────────────┼───────────────┬─────────────────┐
        ▼                ▼              ▼                ▼                 │
┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌────────────────┐   │
│ Retrieval      │ │ Grounding/     │ │ Translation    │ │ Voice          │   │
│ Agent          │ │ Generation     │ │ Agent          │ │ Synthesis Agent│   │
│                │ │ Agent          │ │                │ │                │   │
└───────┬───────┘ └───────┬───────┘ └───────┬───────┘ └────────┬───────┘   │
        │  result          │  result         │  result          │  result   │
        └────────────────→ orchestrator ←─────────────────────────────────┘
                            (updates shared state, decides retry/next/fallback)
                                        │
                                 all stages done
                                        ▼
                                 emits AudioResponseReady
```

**Control flow, concretely:**
1. Orchestrator receives the Captain's command → delegates to **Retrieval Agent**.
2. Retrieval Agent returns chunks + a relevance self-assessment. Orchestrator inspects it:
   - If low relevance → Orchestrator asks Retrieval Agent to reformulate and re-search (bounded retries, e.g. max 2).
   - If still nothing relevant → Orchestrator routes straight to a fallback response, skipping generation.
3. Orchestrator delegates to **Grounding/Generation Agent** with the chunks.
   - If the agent flags it cannot ground the answer → Orchestrator routes back to Retrieval Agent with a refined query, or emits the ungrounded-fallback path.
4. Orchestrator delegates to **Translation Agent**, then **Voice Synthesis Agent**, each a straightforward hand-off since by this point there's no ambiguity left to resolve — but each agent still owns its own retry/fallback logic locally (e.g., Voice Synthesis Agent falling back to a secondary TTS provider) so the Orchestrator doesn't need provider-level knowledge.
5. Orchestrator emits the terminal domain event (`AudioResponseReady` or `PipelineFallback`).

### 7.4 Shared state contract between agents

All agents read/write a single typed **pipeline state object** (a LangGraph `TypedDict`/Pydantic model) rather than passing free-text back and forth — this is what keeps the multi-agent system debuggable and keeps citations from getting lost in translation between agents:

```python
class PipelineState(TypedDict):
    command_id: str
    original_query: str
    target_language: str
    retrieved_chunks: list[ChunkRef]
    retrieval_attempts: int
    grounded_answer: GroundedAnswer | None
    translation: Translation | None
    audio_response: AudioResponse | None
    status: PipelineStatus              # in_progress | grounded | ungrounded | failed
    trace: list[PipelineEvent]          # append-only, powers the required trace log
```

Every agent hand-off appends to `trace`, which is exactly the pipeline_events table from Section 8 — the multi-agent design and the audit-trail requirement are the same mechanism.

### 7.5 Failure & delegation policy (keep the Orchestrator dumb about *how*, smart about *whether*)

The Orchestrator should encode **routing policy** (what to do next given a state), not **domain logic** (how to check grounding, how to call an API) — that logic stays inside each specialist agent or, better, inside the domain layer's pure functions where possible (e.g., `GroundedAnswer.validate()` from Section 6 can be called by the Grounding Agent directly, keeping the "must have citations" invariant in the domain, not duplicated into agent prompts).

| Failure | Handled by | Orchestrator's role |
|---|---|---|
| No relevant chunks after N retries | Retrieval Agent signals it | Route to fallback response, skip remaining agents |
| Answer fails citation check | Grounding Agent signals it | Route back to Retrieval Agent (once) or fallback |
| Translation API error | Translation Agent retries/backs off internally | Only escalate to Orchestrator if all internal retries exhausted → Orchestrator routes to "untranslated + note" fallback |
| TTS provider down | Voice Synthesis Agent falls back to secondary provider internally | Only escalate if all providers fail → Orchestrator routes to "text-only response" fallback |

This division keeps the Orchestrator's own logic small and testable (it's essentially a routing/decision table over `PipelineState`), while each agent's provider-specific resilience stays encapsulated where it belongs.

### 7.6 Where this sits in the folder structure

```
adapters/outbound/orchestration/
├── orchestrator_agent.py        # supervisor graph — the PipelineOrchestratorPort impl
├── agents/
│   ├── retrieval_agent.py
│   ├── grounding_agent.py
│   ├── translation_agent.py
│   └── voice_synthesis_agent.py
├── state.py                     # PipelineState TypedDict/Pydantic model
└── policies.py                  # retry/fallback routing rules used by the orchestrator
```

Only `orchestrator_agent.py` is exposed to the rest of the app via `PipelineOrchestratorPort` — the individual agents are private implementation detail of that one adapter, same as before.

### 7.7 Tradeoff to state plainly in the README

A single flat LangGraph (Section 6) is simpler to reason about and sufficient for a 10–50-doc prototype; the multi-agent supervisor version adds real value once agents need independent judgment (query reformulation, provider fallback) but costs more latency (extra LLM calls for routing decisions) and more moving parts to test. Say you chose multi-agent specifically to demonstrate the pattern and to get clean per-stage fallback behavior — not because the task size demanded it.

---

## 8. CQRS split

| | Write side (Command) | Read side (Query) |
|---|---|---|
| Entry point | `POST /commands` | `GET /conversations/{id}`, `GET /commands/{id}/trace` |
| Handler | `SubmitCaptainCommandHandler` — loads/creates aggregate, invokes pipeline adapter, persists via repository, publishes events | `ConversationReadModel` — simple SQLAlchemy query against denormalized view (or same tables for this scale — no need for a separate read DB at 10–50 docs) |
| Model | Rich domain aggregate (`Command`, `GroundedAnswer`, invariants enforced) | Flat DTOs, no business logic |

At this project's scale, CQRS doesn't need separate databases — it means **separate code paths and separate models**, which keeps write-side validation logic from leaking into read-side DTOs. Document this as a conscious "CQRS-lite" choice in the README so it doesn't look like over-engineering to a reviewer.

---

## 9. Data model (SQLite via SQLAlchemy 2.0 async)

```
conversations
  id (uuid, pk)
  captain_id
  target_language
  created_at

commands
  id (uuid, pk)
  conversation_id (fk)
  input_text
  status            -- pending | grounded | ungrounded | failed
  created_at

retrieved_chunks         -- join table, many-to-many command↔chunk with score
  command_id (fk)
  chunk_id (fk)
  similarity_score

knowledge_chunks
  id (uuid, pk)
  document_id (fk)
  content
  embedding (BLOB / serialized vector — or store only in Chroma/FAISS,
             keep just the id + content here, vectors live in the vector store)

knowledge_documents
  id (uuid, pk)
  title
  source_path

grounded_answers
  id (uuid, pk)
  command_id (fk, unique)
  answer_text
  citations_json      -- list of chunk ids actually cited

translations
  id (uuid, pk)
  answer_id (fk)
  target_language
  translated_text

audio_responses
  id (uuid, pk)
  translation_id (fk)
  voice_profile_id
  audio_path
  duration_ms

pipeline_events              -- append-only trace log (the audit trail)
  id (uuid, pk)
  command_id (fk)
  event_type
  payload_json
  occurred_at
```

**Repository pattern:** `ConversationRepositoryPort` (Protocol) → `SQLiteConversationRepository` (adapter, async SQLAlchemy). Vector embeddings themselves live in Chroma/FAISS (file-based, no separate server needed — fits the "keep it simple" spirit of using SQLite), not duplicated into SQLite.

---

## 10. Knowledge Base Update Workflow (Rule-Based Curation, Multi-Contributor)

The original spec treats the knowledge base as static (10–50 seed docs). Extending it to accept **new incoming information over time — from the Captain and from other users** — needs its own small piece of design, because "just embed whatever comes in" would let bad or duplicate data silently corrupt retrieval quality. Keep this **rule-based, not ML-based** — a simple, auditable predicate chain, not a trained moderation model. That's the right-sized choice: deterministic rules are free, instant, explainable in a demo, and sufficient at this scale.

### 10.1 New domain concept: `KnowledgeSubmission`

A submission is **not** the same aggregate as a `Document`/`Chunk` (Section 4's Knowledge context) — it's a separate lifecycle that only *becomes* a Document once it clears the rules:

```
KnowledgeSubmission
  id
  submitted_by        -- user id (Captain or other Crew/user)
  submitter_role       -- "captain" | "crew" | "guest"
  raw_content
  status               -- pending | approved | rejected | indexed
  rule_results_json    -- which rules passed/failed, for auditability
  created_at
  reviewed_by          -- nullable, set if a human reviewed it
```

This keeps the **existing knowledge base immutable and trustworthy** during the RAG pipeline's normal operation — nothing touches `knowledge_chunks`/the vector store directly; everything goes through the submission → rule-check → approval → index path.

### 10.2 The rule engine (deliberately simple)

A small ordered chain of pure predicate functions, each returning `pass` / `fail` / `needs_review` — implemented as plain Python, not a rules-engine library (Drools/business-rule DSLs would be over-engineering here):

```python
class KnowledgeRule(Protocol):
    def check(self, submission: KnowledgeSubmission, context: RuleContext) -> RuleOutcome: ...

# Example rules, run in order, first hard-fail wins:
rules: list[KnowledgeRule] = [
    MinMaxLengthRule(min_chars=20, max_chars=4000),
    BlocklistKeywordRule(blocklist=load_blocklist()),          # free, local wordlist
    DuplicateSimilarityRule(threshold=0.92),                    # reuses the same embedding
                                                                 # model already in the RAG
                                                                 # pipeline — no extra cost
    TrustedRoleAutoApproveRule(auto_approve_roles={"captain"}), # role-based trust
]
```

**Role-based trust policy** (this is the "rule-based" answer to "and other users"):

| Submitter role | Rule outcome | Result |
|---|---|---|
| `captain` | Passes basic checks (length, blocklist, dedup) | **Auto-approved and indexed immediately** — the Captain is the trusted operator |
| `crew` (other authenticated users) | Passes basic checks | **Goes to `needs_review` queue** — a human (Captain) approves/rejects via a small admin view |
| `crew` | Fails any hard rule (too short/long, blocklisted term, near-duplicate) | **Auto-rejected**, with the specific failed rule stored in `rule_results_json` for transparency |
| `guest` (unauthenticated/low-trust) | Anything | **Always `needs_review`**, never auto-approved, regardless of rule pass |

This is a genuine, demonstrable design pattern — the **Specification/Chain-of-Responsibility pattern** applied to content moderation — without needing an LLM-as-judge call (which would cost tokens and add latency/non-determinism to something that should be fast and explainable).

### 10.3 Flow

```
User submits text ──► KnowledgeSubmission (status=pending)
                              │
                    ┌─────────▼─────────┐
                    │   Rule Engine       │  (domain service, pure function, no I/O
                    │  (chain of rules)   │   except the dedup rule's embedding lookup)
                    └─────────┬─────────┘
              ┌───────────────┼───────────────┐
       hard-fail          needs_review     auto-approve
              │                │                │
     status=rejected   status=pending      status=approved
     (event: Knowledge  (event: Knowledge  (event: Knowledge
      SubmissionRejected) SubmissionQueued)  SubmissionApproved)
                              │                │
                       Captain reviews    ┌────▼─────┐
                       via admin UI       │  Chunk +   │
                       → approve/reject   │  Embed +    │
                              │           │  Index into │
                              └──────────►│  Chroma /   │
                                          │  knowledge_ │
                                          │  chunks     │
                                          └──────┬─────┘
                                                 │
                                          event: KnowledgeIndexed
                                          (now retrievable by RAG pipeline)
```

Every transition is a domain event (`KnowledgeSubmissionQueued`, `KnowledgeSubmissionApproved`, `KnowledgeSubmissionRejected`, `KnowledgeIndexed`) — reusing the same event bus from Section 7, so this doesn't introduce a second infrastructure mechanism.

### 10.4 Ports/adapters touched

No new ports needed beyond what already exists — this is the payoff of having designed `VectorStorePort` and `EventPublisherPort` generically:

- `VectorStorePort.upsert(chunk)` — already exists for ingestion, just called on approval instead of only at seed-time.
- `EventPublisherPort.publish(event)` — same bus as the RAG pipeline trace.
- New **application-layer use cases only** (no new adapters): `SubmitKnowledgeHandler`, `ReviewKnowledgeSubmissionHandler`, `RuleEngineDomainService`.

### 10.5 API surface addition

```
POST   /api/v1/knowledge/submissions              → any authenticated user submits new info
GET    /api/v1/knowledge/submissions?status=pending → Captain/admin views the review queue
POST   /api/v1/knowledge/submissions/{id}/approve  → indexes it (fires KnowledgeIndexed)
POST   /api/v1/knowledge/submissions/{id}/reject   → with optional reason
GET    /api/v1/knowledge/submissions/{id}          → status + rule_results (transparency)
```

### 10.6 Frontend addition (Feature-Sliced)

```
features/
├── submit-knowledge/       # simple form: paste/upload text → submit
└── review-knowledge-queue/ # Captain-only: list of pending submissions,
                             # shows which rules passed/failed, approve/reject buttons
```

`review-knowledge-queue` reuses the same `entities/command`-style status-badge pattern already established for commands (Section 13) — same visual language for "pending/approved/rejected" as pipeline status, so it doesn't feel like a bolted-on second app.

### 10.7 Why this is the right-sized version (not over-engineered)

- No ML moderation model, no LLM-as-judge call, no external moderation API (all would cost money or add non-determinism) — just ordered predicate functions over free-tier tools you already have (the embedding model, a static wordlist).
- No separate "submissions service" or queue infrastructure (Kafka/Celery) — a status column and a polling/read-model query is enough at this scale; note in the README that a background worker (e.g., `arq` or FastAPI `BackgroundTasks`) is the natural next step if submission volume grows, not needed now.
- Role trust is three tiers (`captain`/`crew`/`guest`), not a full RBAC/permissions system — enough to demonstrate "other users can contribute, but rules gate what gets in," without building an auth system the assignment never asked for.

---

## 11. Backend folder structure

```
backend/
├── domain/
│   ├── conversation/
│   │   ├── entities.py         # Command, GroundedAnswer (aggregate root)
│   │   ├── value_objects.py    # Citation, Language, PipelineStatus
│   │   └── events.py           # RetrievalCompleted, AnswerGrounded, ...
│   ├── knowledge/
│   │   └── entities.py         # Document, Chunk
│   └── voice/
│       └── entities.py         # VoiceProfile, Translation, AudioResponse
│
├── application/
│   ├── commands/
│   │   └── submit_captain_command.py   # SubmitCaptainCommandHandler
│   ├── queries/
│   │   └── get_conversation_trace.py
│   └── ports/                          # Protocol interfaces — the "hexagon" boundary
│       ├── llm_port.py
│       ├── vector_store_port.py
│       ├── translator_port.py
│       ├── tts_port.py
│       ├── pipeline_orchestrator_port.py
│       ├── conversation_repository_port.py
│       └── event_publisher_port.py
│
├── adapters/
│   ├── inbound/
│   │   ├── api/
│   │   │   ├── routers/commands.py
│   │   │   ├── routers/conversations.py
│   │   │   └── sse.py                  # live pipeline trace stream
│   │   └── cli.py                      # optional CLI entrypoint
│   └── outbound/
│       ├── orchestration/              # implements PipelineOrchestratorPort — see §7.6 for the
│       │   │                           # full multi-agent breakdown (orchestrator_agent.py, agents/, state.py, policies.py)
│       │   └── orchestrator_agent.py
│       ├── llm/ollama_adapter.py        # free/local — default for demo
│       ├── llm/anthropic_adapter.py     # paid — behind same LLMPort, off by default
│       ├── vector_store/chroma_adapter.py    # free/local
│       ├── translation/argos_adapter.py      # free/offline — default for demo
│       ├── translation/llm_translator_adapter.py  # fallback: ask the local LLM to translate
│       ├── tts/coqui_adapter.py          # free/local — default for demo
│       ├── tts/edge_tts_adapter.py       # free, lighter-weight fallback
│       ├── tts/elevenlabs_adapter.py     # paid voice cloning — behind same TTSPort, off by default
│       ├── persistence/
│       │   ├── models.py               # SQLAlchemy ORM models
│       │   └── sqlite_repository.py
│       └── events/in_memory_bus.py
│
├── config/
│   ├── settings.py                     # pydantic-settings, env-driven
│   └── di_container.py                 # wires ports → adapters (composition root)
│
├── tests/
│   ├── unit/domain/                    # no I/O, pure logic
│   ├── integration/adapters/           # real SQLite (tmp file), fake LLM
│   └── e2e/                            # full pipeline against test doubles
│
├── main.py                             # FastAPI app factory
├── pyproject.toml
└── README.md
```

The **composition root** (`di_container.py`) is the only place that knows concrete adapter classes — everything else is injected via FastAPI's `Depends()` against port types. This is what makes the hexagon real rather than aspirational.

---

## 12. API surface

```
POST   /api/v1/commands                 → submit a Captain text command (async, kicks off pipeline)
GET    /api/v1/commands/{id}            → status + final result (answer, translation, audio url)
GET    /api/v1/commands/{id}/trace      → full pipeline_events trace (retrieved chunks, citations, timings)
GET    /api/v1/commands/{id}/stream     → SSE stream of pipeline_events as they happen
GET    /api/v1/conversations/{id}       → conversation history (read model)
GET    /api/v1/audio/{audio_response_id}→ stream the synthesized audio file
POST   /api/v1/knowledge/documents      → (admin, seed-time) bulk-load initial KB documents
POST   /api/v1/knowledge/submissions              → any user submits new info (see §10.5 for the full set)
GET    /api/v1/knowledge/submissions?status=pending → review queue
GET    /api/v1/health
```

Async by default: `POST /commands` returns `202 Accepted` + a command id immediately; the client follows up with `/stream` (SSE) or polls `/commands/{id}`. This matches how voice-pipeline latency actually behaves (retrieval + LLM + translation + TTS can be several seconds) and avoids a hanging HTTP request.

---

## 13. Frontend architecture (Feature-Sliced Design)

```
frontend/
├── src/
│   ├── app/                    # app shell, providers, router, global styles
│   ├── pages/
│   │   └── console/            # the main Captain console page (composes features)
│   ├── features/
│   │   ├── submit-command/     # input box + submit button + validation
│   │   ├── pipeline-trace/     # live SSE-driven stage-by-stage progress view
│   │   ├── audio-playback/     # audio player for the synthesized response
│   │   ├── conversation-history/
│   │   ├── submit-knowledge/         # §10.6 — form to propose new KB info
│   │   └── review-knowledge-queue/   # §10.6 — Captain-only approve/reject view
│   ├── entities/                # domain-shaped types + minimal display logic
│   │   ├── command/              # Command type, status badge component
│   │   ├── grounded-answer/      # citation chip component
│   │   ├── audio-response/
│   │   └── knowledge-submission/ # submission status type, reused status-badge component
│   ├── shared/
│   │   ├── api/                  # typed API client (generated from OpenAPI or hand-written)
│   │   ├── ui/                   # design-system primitives (Button, Card, Spinner)
│   │   └── lib/                  # hooks, formatters
│   └── main.tsx
```

- **FSD mirrors the backend's bounded contexts** 1:1 at the `entities/` layer (`command`, `grounded-answer`, `audio-response`) — a reviewer can trace a backend aggregate to its frontend entity slice directly.
- **State:** React Query (TanStack Query) for server state (commands, history, trace) — no Redux needed for a console this size. Local UI state via `useState`/`useReducer` inside each feature.
- **Real-time:** native `EventSource` for SSE trace streaming, with a small `usePipelineTrace(commandId)` hook in `features/pipeline-trace`.
- **Typed contract:** generate a TS client from FastAPI's OpenAPI schema (`openapi-typescript` or `orval`) so frontend/backend never drift.

### Key UI states to design for
1. **Idle** — input box ready.
2. **In-flight** — stage-by-stage trace lights up (retrieve → grade → generate → translate → synthesize) as SSE events arrive.
3. **Grounded success** — answer text + citation chips (linking back to source chunks) + audio player, in target language.
4. **Ungrounded fallback** — explicit "I don't have grounded information for this" state (never silently hallucinate — surface it).
5. **Error** — per-stage error surfaced (e.g., "TTS provider failed" vs "no relevant documents found") rather than a generic failure.

---

## 14. Cross-cutting concerns

- **Event-driven trace/logging:** `EventPublisherPort` → in dev, an in-memory bus that also persists to `pipeline_events`; in prod, could be swapped for Redis pub/sub without touching domain code.
- **Config:** `pydantic-settings`, one `.env`, all adapter credentials (Anthropic key, ElevenLabs key, translation provider) injected at the composition root only.
- **Testing pyramid:**
  - Domain: pure unit tests, no mocks needed (no I/O to mock).
  - Application layer: use fakes for all ports (`FakeLLM`, `FakeVectorStore`) — fast, deterministic.
  - Adapters: integration tests against real SQLite (tmp file) and, where possible, recorded HTTP cassettes (`vcrpy`) for LLM/TTS/translation calls so tests don't burn API quota.
- **Observability:** every pipeline event carries a timestamp + duration, so `/commands/{id}/trace` doubles as a performance breakdown (how much time in retrieval vs. LLM vs. TTS) — useful for the "known limitations" section of the README.

---

## 15. What to explicitly call out as a tradeoff in the README

- **Everything runs free and local by design, not by accident** — Ollama, Chroma, sentence-transformers, Argos Translate, Coqui/edge-tts, SQLite. Say this up front; it's a feature (zero-setup-friction demo for the reviewer), not a corner cut.
- Voice *cloning* specifically is the one place the free stack is honestly weaker than the paid suggestion (ElevenLabs) — ship a single consistent preset voice and say so plainly, rather than overclaiming. The `TTSPort` interface doesn't care which is behind it, which is the actual point being demonstrated.
- Local LLM quality/speed (Ollama on CPU) is lower than Claude/GPT-4 — grounding/citation checks may need a slightly more lenient prompt than a frontier model would. Note this as a known limitation, not a bug.
- CQRS is "lite" (shared DB) — right-sized for this scale, not a claim of horizontal scalability.
- SQLite is fine for a prototype/single-writer; note the migration path to Postgres, or to the paid adapters (Anthropic/ElevenLabs), is just a swap in `di_container.py` — nothing else changes. This is the concrete payoff of the hexagonal boundary, worth pointing at directly in the demo video.
- LangGraph adds real value here specifically because of the grounding-retry loop and multi-stage trace requirement — call that out so it doesn't read as buzzword-driven.
- Multi-agent (Section 7) is documented and structurally ready for, but the demo should run on the flat pipeline (Section 6) unless there's clearly time left over — don't let showing off the pattern risk a working submission.

---

## 16. Suggested build order (fits the "prioritize RAG > translation > voice" guidance)

1. Domain entities + ports (no I/O) + unit tests for invariants.
2. `SQLiteConversationRepository` + migrations.
3. Knowledge ingestion + Chroma adapter + retrieval, tested in isolation.
4. **Flat LangGraph pipeline first** (Section 6): retrieve → generate → verify-grounding. Get this solid and working end-to-end before touching agents — it's your safety net.
5. Translation node + adapter, TTS node + adapter (single voice profile) added to the flat graph.
6. FastAPI routers + SSE streaming, wired to the flat graph. **You now have a fully working, demoable system.**
7. Frontend console (submit-command → pipeline-trace → audio-playback), wired to the working backend.
8. **Knowledge Base update workflow** (Section 10): submission endpoint + rule engine + review queue + frontend `submit-knowledge`/`review-knowledge-queue` slices. This is the next-highest-value addition after the core demo works, since it directly answers "can the KB grow" — do it before the multi-agent refactor unless you specifically want to showcase agents.
9. *If time remains:* refactor into the multi-agent supervisor design (Section 7) — split Retrieval and Grounding into agents with their own retry/reformulation judgment first (highest payoff), Translation/Voice Synthesis agents last (lowest payoff, since they're mostly deterministic).

This order means the multi-agent pattern is a **strict upgrade you layer on**, never a blocker to having something working before the deadline.
