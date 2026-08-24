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

---

## Current status

Built milestone by milestone; a milestone is marked done only after it has been
executed and verified, never merely written.

| Milestone | Scope | Status |
|---|---|---|
| 0 | Repository & environment audit | ✅ Verified |
| 1 | Foundation — auth, RBAC, schema, health, demo users | ✅ Verified |
| 2 | Competency system, evidence ledger, deterministic engine | Not started |
| 3 | Document upload, RAG, grounded MCQ, SME review | Not started |
| 4 | Statistical simulation lab | Not started |
| 5 | Gap detection & explainable recommender | Not started |
| 6 | Dashboards, learning catalogue, iGOT boundary | Not started |
| 7 | End-to-end demo wiring | Not started |
| 8 | Testing & polish | Not started |

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
