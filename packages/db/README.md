# cadence-db

Shared SQLAlchemy models — `User`, `LoginSecurity`, `UserSession`, `Analysis` — used by both `apps/api` and `apps/worker`. Both processes read `DATABASE_URL` and talk to the same Postgres (or SQLite, the default/test fallback) directly; there's no callback API between them. This is what lets `apps/worker`'s `detect_tracks_job` write a finished `AnalysisResult` straight into the row `apps/api`'s `GET /analyses/{id}` reads back.

Moved out of `apps/api` (where it started in Phase 1) once `apps/worker` needed to write to the same rows in Phase 2 — see [`../../docs/decisions.md`](../../docs/decisions.md) and [`../../STATUS.md`](../../STATUS.md) for why shared-DB was chosen over a callback API.

## Install

```bash
pip install -e .
```

(Already listed as `-e ../../packages/db` in `apps/api/requirements.txt` and `apps/worker/requirements.txt`.)

## Migrations

None yet — `init_db()` just runs `Base.metadata.create_all`, which only adds missing tables/columns, never alters or drops. Fine until the schema needs to change without losing data; move to Alembic before then (flagged in `STATUS.md` since Phase 1).
