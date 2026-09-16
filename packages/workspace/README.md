# cadence-workspace

Per-analysis file workspace helpers — `apps/api` writes uploaded videos into one of these (UUID-isolated, path-jailed on delete), `apps/worker` reads them back to run detection/pose on. Both need to agree on where `runtime/` actually lives, which is why this moved out of `apps/api` in Phase 2: the default root is resolved relative to this package's own location in the monorepo checkout (`<repo_root>/runtime`), not relative to whichever app imports it, so the two processes agree without either one setting `CADENCE_RUNTIME_DIR` by hand for local dev.

Originally ported from `legacy/cadence-streamlit/modules/workspace.py` in Phase 1.

## Install

```bash
pip install -e .
```

(Already listed as `-e ../../packages/workspace` in `apps/api/requirements.txt` and `apps/worker/requirements.txt`.)

## `CADENCE_RUNTIME_DIR`

Set explicitly once uploads move to object storage instead of local disk (Phase 7) — see [`../../.env.example`](../../.env.example).
