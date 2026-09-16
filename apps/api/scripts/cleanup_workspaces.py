#!/usr/bin/env python
"""Remove abandoned analysis workspaces older than --max-age-hours.

Intended to run on a schedule (cron / Windows Task Scheduler / a
platform scheduled job) against the same CADENCE_RUNTIME_DIR both
apps/api and apps/worker use (packages/workspace, shared by both now
that apps/worker actually reads uploaded videos). Not run from inside
apps/worker itself -- keeping cleanup on a separate schedule rather
than tied to job execution -- and this local-disk assumption goes away
once Phase 7 moves uploads to object storage.
"""

from __future__ import annotations

import argparse

from cadence_workspace import cleanup_abandoned_workspaces


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
