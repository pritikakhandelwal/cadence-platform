# apps/api — Cadence BFF

FastAPI backend-for-frontend. Owns auth, uploads, and the `AnalysisResult` API surface once Phase 1/2 land.

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

`GET /health` → `{"status": "ok"}`.

## Test

```bash
pytest
```

## Roadmap

Currently Phase 0 (health endpoint only). Phase 1 ports the already-working `auth`/`input_validation`/`video_validation`/`workspace` modules from [`legacy/cadence-streamlit/modules`](../../legacy/cadence-streamlit/modules) onto this app and a Postgres database, rather than rewriting them. See [`../../STATUS.md`](../../STATUS.md).
