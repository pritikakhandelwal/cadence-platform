# Cadence

A broadcast-grade dance coaching platform: lock onto the intended dancer in messy video, align their motion to a reference, and return timestamped, body-part-specific coaching — then route them to the next form, phrase, and track.

Full plan: [`ROADMAP.md`](ROADMAP.md). Current build state: [`STATUS.md`](STATUS.md). Product/scoping decisions and why: [`docs/decisions.md`](docs/decisions.md).

## Layout

```text
apps/
  web/      Next.js Arena UI (placeholder in Phase 0, real UI from Phase 4)
  api/      FastAPI BFF — auth, uploads, AnalysisResult API
  worker/   arq background jobs — pose/tracking, alignment/scoring
packages/
  schema/   the canonical AnalysisResult contract (Python + TypeScript)
legacy/
  cadence-streamlit/   the original Streamlit prototype, kept runnable for reference
docs/
  decisions.md   why certain features are scoped the way they are
```

Every app has its own README with setup/run/test instructions:
[`apps/web`](apps/web/README.md) · [`apps/api`](apps/api/README.md) · [`apps/worker`](apps/worker/README.md) · [`packages/schema`](packages/schema/README.md) · [`legacy/cadence-streamlit`](legacy/cadence-streamlit/README.md)

## Quick start (Phase 0 — everything here is a placeholder proving the skeleton works)

```bash
# web
cd apps/web && npm install && npm run dev        # http://localhost:3000

# api (separate terminal)
cd apps/api && python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000        # GET /health

# worker (separate terminal, needs Redis running)
cd apps/worker && python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt
arq worker.settings.WorkerSettings

# legacy prototype (separate terminal — still the only thing with real coaching logic today)
cd legacy/cadence-streamlit && python -m venv .venv && .venv\Scripts\activate
pip install -r requirements-utf8.txt
streamlit run app.py
```

FFmpeg must be on `PATH` for both the legacy app and (later) `apps/api` video validation.

## Where things actually stand

Don't assume a phase in `ROADMAP.md` is unstarted just because it's early in the list — the legacy app already has working auth (Argon2id + lockout), upload validation (magic bytes + ffprobe), and per-analysis workspace isolation. Read [`STATUS.md`](STATUS.md) before starting work on any phase; it tracks what's actually done vs. planned, since the two drift.

## Contributing to this repo

- The `AnalysisResult` shape in [`packages/schema`](packages/schema) is the one contract every layer speaks. If you need a new field on an analysis, add it there first, in both languages, in the same commit.
- Follow the phase order in [`ROADMAP.md § 6`](ROADMAP.md#6-priority-order-non-negotiable) — it's non-negotiable for a reason (see the "Risk" notes under each phase).
- Update [`STATUS.md`](STATUS.md) when you finish a phase item.
