# SAKSHYA

**Evidence-based competency intelligence for India's Official Statistical System.**

Smart India Hackathon 2026 — Problem Statement 26101.

> Traditional learning: `Course → Completion → Certificate`
>
> SAKSHYA: `Role → Competency → Assessment → Evidence → Competency Inference → Gap → Intervention → Practice → New Evidence`

SAKSHYA does not treat course completion as proof of competency. It builds an
auditable evidence trail from assessments, practical simulations and reviewed
learning activity, and uses it to determine competency gaps and what a learner
should do next — with the reasoning always inspectable.

> ⚠️ **Prototype.** All seeded content is illustrative sample data. It is **not**
> official Government of India competency data, and no live iGOT Karmayogi
> integration is implemented or simulated.

---

## Quick start

Requires Python 3.11+ and Node 18+. No Docker or PostgreSQL needed.

**1. Backend**

```bash
cd backend
python -m venv .venv
```

```bash
.venv/Scripts/python -m pip install -r requirements.txt
```

```bash
.venv/Scripts/python -m app.db.seed
```

```bash
.venv/Scripts/python -m uvicorn app.main:app --port 8000
```

**2. Frontend** (new terminal)

```bash
cd frontend && npm install && npm run dev
```

Open <http://localhost:5173>. API docs at <http://localhost:8000/docs>.

### Demo accounts

Development-only credentials, seeded by `app.db.seed`. The login screen has
one-click buttons for each.

| Role | Email | Password |
|---|---|---|
| Learner | `learner@sakshya.dev` | `Sakshya@2026` |
| SME | `sme@sakshya.dev` | `Sakshya@2026` |
| Admin | `admin@sakshya.dev` | `Sakshya@2026` |

### Tests

```bash
cd backend && .venv/Scripts/python -m pytest
```

```bash
cd frontend && npm test
```

202 backend tests and 19 frontend tests. The backend suite covers the
deterministic engines against hand-computed values, RBAC across every
role pair, grounding verification, and the full evidence loop.

### Reset the demo

```bash
cd backend && rm -f sakshya.db && .venv/Scripts/python -m app.db.seed
```

The 2-minute demo script is in [docs/DEMO.md](docs/DEMO.md).

---

## Current status

Built milestone by milestone; a milestone is marked done only after it has been
executed and verified, never merely written.

| Milestone | Scope | Status |
|---|---|---|
| 0 | Repository & environment audit | ✅ Verified |
| 1 | Foundation — auth, RBAC, schema, health, demo users | ✅ Verified |
| 2 | Competency system, evidence ledger, deterministic engine | ✅ Verified |
| 3 | Document upload, RAG, grounded MCQ, SME review | ✅ Verified |
| 4 | Statistical simulation lab | ✅ Verified |
| 5 | Gap detection & explainable recommender | ✅ Verified |
| 6 | Dashboards, learning catalogue, iGOT boundary | ✅ Verified |
| 7 | End-to-end demo wiring | ✅ Verified |
| 8 | Testing & polish | ✅ Verified |

## How competency is determined

Mastery is the recency-weighted, type-weighted mean of **accepted** evidence:

```
mastery = Σ(type_weight × recency × score) / Σ(type_weight × recency)
```

Evidence type weights encode the project's core claim — attendance is not
capability:

| Evidence type | Weight |
|---|---|
| Simulation | ×1.5 |
| Practical submission (SME reviewed) | ×1.4 |
| Expert verified | ×1.2 |
| Assessment | ×1.0 |
| Peer review | ×0.8 |
| **Course completion** | **×0.4** |

Confidence is calculated **separately** from mastery, from four components —
evidence volume, type diversity, recency, and agreement between scores. Below
1.5 effective evidence weight or 0.35 confidence, SAKSHYA reports
`INSUFFICIENT_EVIDENCE` and asserts **no level at all**.

The seeded demo makes this concrete: the learner scored **95% on a
non-response course**, and SAKSHYA still refuses to claim the competency —
one weak evidence type carries only 0.37 effective weight. Every figure is
reproducible by hand from `GET /api/v1/competency-method`, which publishes the
constants used.

## How generated questions stay honest

```
Upload → extract (page-aware) → chunk (heading-aware) → embed
      → retrieve → draft → VERIFY GROUNDING → tag competency → SME review
```

The generator is **extractive**: every stem, correct answer and distractor is
lifted from real sentences in the uploaded document, so it cannot hallucinate
a fact or invent a citation. Distractors are real statements from *other*
passages of the same document — plausible, but wrong answers to the question
asked.

Each draft is then checked against the chunk it cites, verifying two separate
claims: that the passage really contains the quote, and that the answer marked
correct actually appears in it. Failures are stored **flagged**, not discarded,
so a generation failure is visible to a reviewer rather than silently dropped.
An SME edit re-runs the same verification — grounding is never assumed to
survive an edit.

Competency tags are AI *suggestions*, accepted only when the best match is both
close enough and clearly closer than the runner-up. In the seeded demo 4 of 8
questions are tagged and 4 are deliberately left untagged for the expert —
guessing would be worse than admitting uncertainty.

**Learners only ever see approved questions.** Nothing unreviewed reaches an
assessment.

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). The central constraint:

> AI may **generate** content. AI may never **score** competency.

Mastery, confidence, gap severity, prerequisites and recommendation ranking are
deterministic functions over the evidence ledger, isolated in `app/engines/`.
AI is confined to `app/ai/` and never feeds those calculations.

## Technology

| Layer | Choice |
|---|---|
| Frontend | React 18, TypeScript, Vite, React Router |
| Backend | FastAPI, Pydantic v2, SQLAlchemy 2 |
| Auth | JWT (PyJWT) + bcrypt, role-based access control |
| Database | SQLite locally; PostgreSQL + pgvector as deployment target |
| AI | Provider-agnostic LLM/embedding interfaces, offline deterministic mock by default |

**On the database and Docker:** the development machine has no Docker and no
usable pgvector, so persistence and vector search sit behind interfaces and run
on SQLite locally. `docker-compose.yml` describes the PostgreSQL + pgvector
target and is explicitly labelled **unverified** — it has not been built here.
Reasoning in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Security notes

- No API key or production secret is committed. `SAKSHYA_SECRET_KEY` comes from
  the environment, and the app **refuses to start** outside development without
  it.
- Demo credentials are development fixtures only.
- Login returns an identical error for an unknown email and a wrong password, so
  account existence is not disclosed.
- Authorisation is re-checked against the database on every request, so a
  deactivated user or a changed role takes effect immediately rather than when
  the token expires.
- Uploaded filenames are sanitised and UUID-prefixed, so a crafted name cannot
  escape the upload directory. Internal storage paths are never returned to
  clients.
- A rejected token ends the session client-side rather than stranding the user
  on an error.

## Known limitations

Stated plainly rather than left for a judge to find:

- **`docker-compose.yml`, `backend/Dockerfile` and `app/vectorstore/pgvector_store.py`
  have never been executed.** The build machine has no Docker and no pgvector.
  They are labelled unverified in-file and must not be reported as working
  until they have actually been run.
- **Embeddings are lexical, not semantic.** The offline provider is a hashed
  bag-of-words projection: it matches wording, not paraphrase. Adequate at demo
  corpus size; a real embedding model drops in behind the same interface.
- **Generated questions are extractive**, so they read more plainly than a
  hosted LLM's would. That is the trade that buys non-hallucination.
- **Document ingestion is synchronous.** A large PDF would block the request;
  production would need a queue. The whole upload is also read into memory
  before the size limit is checked.
- **Scanned/image PDFs are rejected** with a message saying OCR would be
  required, rather than silently producing nothing.
- **Schema is created from SQLAlchemy metadata plus an idempotent seed**, not
  incremental migrations. Alembic is the documented production path.
