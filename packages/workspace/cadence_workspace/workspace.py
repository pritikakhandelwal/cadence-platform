"""Per-analysis file workspaces, shared by apps/api and apps/worker.

Originally ported from legacy/cadence-streamlit/modules/workspace.py.
Moved to a shared package (rather than living inside apps/api) because
apps/worker needs to read the same upload files apps/api wrote --
without this, the two processes would need their own private copy of
this path logic and could silently drift.

The default runtime root is resolved relative to this package's
location in the monorepo checkout (<repo_root>/runtime), not relative
to whichever app imports it -- so apps/api and apps/worker agree on
the same directory without either one having to set CADENCE_RUNTIME_DIR
by hand for local dev. Set CADENCE_RUNTIME_DIR explicitly in production
once this points at object storage instead of a local disk (Phase 7).

Uploaded videos and generated artifacts must never use shared fixed
filenames. Each analysis run receives an isolated directory under
``runtime/analyses``.
"""

from __future__ import annotations

import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

# cadence_workspace/workspace.py -> cadence_workspace -> workspace -> packages -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[3]


def _runtime_root() -> Path:
    configured_root = os.getenv("CADENCE_RUNTIME_DIR")
    return Path(configured_root) if configured_root else _REPO_ROOT / "runtime"


@dataclass(frozen=True)
class AnalysisWorkspace:
    """Locations reserved for one dance analysis."""

    run_id: str
    root: Path

    @property
    def professional_upload(self) -> Path:
        return self.root / "professional_upload.mp4"

    @property
    def user_upload(self) -> Path:
        return self.root / "user_upload.mp4"

    @property
    def professional_normalized(self) -> Path:
        return self.root / "professional_normalized.mp4"

    @property
    def user_normalized(self) -> Path:
        return self.root / "user_normalized.mp4"

    @property
    def professional_keypoints(self) -> Path:
        """npz with `keypoints` (N, 17, 2), `frame_indices` (N,), `fps` (scalar) --
        written by apps/worker's pose jobs (Phase 2), read by Phase 3 scoring."""
        return self.root / "professional_keypoints.npz"

    @property
    def user_keypoints(self) -> Path:
        return self.root / "user_keypoints.npz"

    @property
    def overlay(self) -> Path:
        return self.root / "overlay.mp4"


def workspace_for(run_id: str, base_dir: Path | None = None) -> AnalysisWorkspace:
    """Reconstruct the workspace for an existing run_id (e.g. from a
    worker job that only has Analysis.workspace_id, not the original
    AnalysisWorkspace object)."""

    analyses_dir = base_dir or (_runtime_root() / "analyses")
    return AnalysisWorkspace(run_id=run_id, root=analyses_dir / run_id)


def create_analysis_workspace(base_dir: Path | None = None) -> AnalysisWorkspace:
    """Create an isolated workspace for one analysis run."""

    analyses_dir = base_dir or (_runtime_root() / "analyses")
    run_id = uuid4().hex
    root = analyses_dir / run_id
    root.mkdir(parents=True, exist_ok=False)
    return AnalysisWorkspace(run_id=run_id, root=root)


def remove_analysis_workspace(workspace: AnalysisWorkspace) -> None:
    """Remove a workspace after its artifacts are no longer needed."""

    analyses_dir = (_runtime_root() / "analyses").resolve()
    workspace_root = workspace.root.resolve()
    if analyses_dir not in workspace_root.parents:
        raise ValueError("Refusing to remove a directory outside the analyses runtime path.")
    shutil.rmtree(workspace_root, ignore_errors=True)


def cleanup_abandoned_workspaces(max_age_hours: float = 24, base_dir: Path | None = None) -> list[str]:
    """Remove workspace directories older than max_age_hours.

    Intended to run on a schedule (see apps/api/scripts/cleanup_workspaces.py)
    so a crashed upload or an analysis nobody ever finished doesn't leak
    disk forever. Returns the run_ids removed.
    """

    analyses_dir = base_dir or (_runtime_root() / "analyses")
    if not analyses_dir.is_dir():
        return []

    cutoff = time.time() - max_age_hours * 3600
    removed: list[str] = []
    for entry in analyses_dir.iterdir():
        if not entry.is_dir():
            continue
        if entry.stat().st_mtime < cutoff:
            shutil.rmtree(entry, ignore_errors=True)
            removed.append(entry.name)
    return removed
