# Deploying SAKSHYA

SAKSHYA deploys as **one service**. The FastAPI process serves both the API and
the built frontend, so there is a single origin — no CORS configuration, no
reverse proxy, and no API base URL for the client to get wrong.

```
        ┌─────────────────────────────────────┐
        │  uvicorn (one process, one port)    │
        │                                     │
        │  /                → frontend/dist   │
        │  /assets/*        → JS + CSS        │
        │  /api/v1/*        → FastAPI routes  │
        │  /learner/...     → index.html      │  (client-side routes)
        └─────────────────────────────────────┘
```

---

## Before you deploy: should you?

**For the 2-minute judged demo, run it locally.** Free hosting tiers sleep after
inactivity and take 30–60 seconds to wake. In a two-minute slot that is fatal.
Local start-up is instant, needs no venue wifi, and cannot fail on someone
else's infrastructure.

Deploy anyway for the submission form, for judges who browse later, and as
insurance if your laptop dies — just don't make it the primary path.

---

## Render (blueprint included)

[`render.yaml`](../render.yaml) describes the service.

1. Push the branch to GitHub.
2. Render → **New → Blueprint** → pick the repository.
3. Render reads `render.yaml`, generates `SAKSHYA_SECRET_KEY`, and deploys.

Health check is `/api/v1/health`, which round-trips a real database query
rather than returning a hard-coded `ok`.

> **Not verified from this machine.** The build and start commands are the ones
> tested locally; Render's behaviour around them has not been exercised here.
> Treat the first deploy as the real test.

## Any other host

Two commands. Anything that runs Python 3.12 and Node 18 will do.

**Build:**

```bash
./scripts/build.sh
```

**Start:**

```bash
cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

---

## Environment variables

| Variable | Required | Notes |
|---|---|---|
| `SAKSHYA_SECRET_KEY` | **Yes** | JWT signing key. The app **refuses to boot** when `SAKSHYA_ENVIRONMENT` is not `development` and this is unset — that guard is deliberate, not a bug. Generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `SAKSHYA_ENVIRONMENT` | Recommended | Set to `production`. Anything else is treated as development. |
| `SAKSHYA_AUTO_SEED` | No (default `true`) | Seeds prototype demo data **only when the database is empty**. Never overwrites existing data. Set `false` once you have real data. |
| `SAKSHYA_DATABASE_URL` | No | Defaults to SQLite. See the database note below. |
| `SAKSHYA_CORS_ORIGINS` | No | Irrelevant in a single-service deploy — same origin means no cross-origin requests. |

Never commit a real secret. `.env` is gitignored; `.env.example` documents the
shape without values.

---

## The database

The default is SQLite in the working directory. On a free tier with an
ephemeral disk that file is **lost on every restart** — which is why auto-seed
exists: the deployment comes back with the full prototype demo rather than an
empty screen.

That is fine for a prototype and wrong for anything real. For durability,
either attach a persistent disk, or point `SAKSHYA_DATABASE_URL` at PostgreSQL:

```
SAKSHYA_DATABASE_URL=postgresql+psycopg://user:pass@host:5432/sakshya
```

The models are driver-agnostic, so that part works. Two caveats, stated
honestly:

- `psycopg` is **not** in `requirements.txt` — add it before switching.
- The pgvector adapter in `app/vectorstore/pgvector_store.py` **has never been
  executed**. The build machine had no Docker and no pgvector. Retrieval falls
  back to exact numpy cosine, which returns the same neighbours at this corpus
  size. See [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Verifying a deploy

```bash
curl -s https://YOUR-URL/api/v1/health
```

Expect `{"status":"ok",...,"database":"connected"}`. Then open the root URL and
sign in with a demo account — the login screen has one-click buttons.

If the page loads but every API call fails, the frontend was not built: check
that `frontend/dist` exists in the deployed image. `GET /api` reports
`frontend_bundled` so you can confirm it without guessing.
