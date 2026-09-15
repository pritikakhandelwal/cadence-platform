# apps/worker — Cadence background jobs

`arq` worker for anything too slow to run in-request: pose/tracking (Phase 2), alignment/scoring (Phase 3), cleanup jobs (Phase 1/7).

## Run locally

Requires Redis running locally (`redis-server`, or `docker run -p 6379:6379 redis`).

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
arq worker.settings.WorkerSettings
```

## Test

```bash
pytest
```

Tests call job functions directly — no live Redis needed for CI.

## Roadmap

Currently Phase 0 (one `echo` job only). Real jobs land in Phase 2 (detect → track → pose) and Phase 3 (align → score → segment). See [`../../STATUS.md`](../../STATUS.md).
