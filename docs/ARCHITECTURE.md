# SAKSHYA — Architecture

## The one rule the codebase enforces structurally

> AI may **generate** content. AI may never **score** competency.

Everything that determines a competency level, confidence, gap, prerequisite or
recommendation ranking lives in `backend/app/engines/` as pure, deterministic,
unit-testable functions. Nothing in `backend/app/ai/` is permitted to influence
those numbers. This is an import-direction rule, not a convention:

```
app/api  ──▶ app/engines   (deterministic: mastery, confidence, gap, ranking)
app/api  ──▶ app/ai        (generative: chunking, MCQ drafting, debrief text)

app/ai   ──X app/engines   (forbidden — AI never feeds the scorers)
```

The result is that "why does SAKSHYA believe I have this competency level?" is
always answerable by replaying arithmetic over the evidence ledger.

## Layout

```
backend/app/
  core/         config, JWT security, RBAC dependencies
  db/           engine/session, declarative base, idempotent seed
  models/       SQLAlchemy ORM models
  schemas/      Pydantic request/response contracts
  api/v1/       HTTP routes
  engines/      deterministic competency / gap / recommendation maths  (M2, M5)
  ai/           provider-agnostic LLM + embedding abstractions, RAG    (M3)
  vectorstore/  VectorStore protocol + numpy and pgvector adapters     (M3)
  catalog/      LearningCatalogAdapter + local adapter (iGOT boundary) (M6)
frontend/src/
  api/          fetch client with typed errors
  auth/         session context
  components/   shell, route guards
  pages/        role dashboards
```

## Persistence: why SQLite locally

The target stack is PostgreSQL + pgvector. The development machine used to
build this prototype has:

- no Docker installed,
- only PostgreSQL 10 (end-of-life, stopped),
- no pgvector, and no MSVC build tools to compile it,
- ~8.7 GB free disk.

Rather than write a pgvector-dependent stack that could never be run or tested
here — and then claim it worked — persistence and vector search sit behind
interfaces:

- **Relational**: SQLAlchemy models, driver-agnostic. Swap
  `SAKSHYA_DATABASE_URL` to a PostgreSQL URL and the same models apply.
- **Vector search** (Milestone 3): a `VectorStore` protocol with two adapters —
  a numpy exact-cosine store used locally, and a pgvector store for
  PostgreSQL. Exact cosine over a demo-sized corpus returns the same neighbours
  an ANN index would; the index matters at a scale this prototype does not
  reach.

`docker-compose.yml` and `backend/Dockerfile` describe the PostgreSQL target and
are labelled **unverified** — they have not been built here.

## AI providers: why an offline mock

No AI API key is present in this environment, so the default provider is a
deterministic offline mock:

- **Embeddings** — hashed character/word n-grams projected into a fixed-dimension
  normalised vector. Deterministic, dependency-free, and adequate for lexical
  retrieval over a small corpus. Avoids `torch`/`sentence-transformers`, which
  the disk budget cannot accommodate.
- **MCQ generation** — extractive: stems and options are built from sentences in
  the actually-retrieved chunks, so every citation points at real source text.
  Items that cannot be grounded are flagged rather than emitted.

Setting a real provider key swaps the implementation without touching call
sites. The mock remains the fallback so a live demo cannot fail on a network
error.

## Schema management

The prototype creates its schema from SQLAlchemy metadata (`create_all`) plus an
idempotent seed, because the demo database is rebuilt from seed data rather than
migrated in place. Alembic is the documented path for production, where
incremental migration against real data matters.

## Prototype data labelling

Sample records carry an `is_prototype_data` flag in the database, the API
response, and a persistent banner in the UI. No official Government of India
competency mapping is reproduced or implied.
