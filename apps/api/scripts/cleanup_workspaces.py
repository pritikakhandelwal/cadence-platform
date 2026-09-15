#!/usr/bin/env python
"""Remove abandoned analysis workspaces older than --max-age-hours.

Intended to run on a schedule (cron / Windows Task Scheduler / a
platform scheduled job) against the same CADENCE_RUNTIME_DIR the API
process uses. Not wired into apps/worker because the worker doesn't
necessarily share a filesystem with the API in production (object
storage replaces local workspaces in Phase 7 anyway).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.workspace import cleanup_abandoned_workspaces  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-age-hours", type=float, default=24)
    args = parser.parse_args()

    removed = cleanup_abandoned_workspaces(max_age_hours=args.max_age_hours)
    print(f"Removed {len(removed)} abandoned workspace(s).")
    for run_id in removed:
        print(f"  - {run_id}")


if __name__ == "__main__":
    main()
