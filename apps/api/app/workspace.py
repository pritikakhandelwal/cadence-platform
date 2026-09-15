"""Per-analysis file workspaces.

Ported from legacy/cadence-streamlit/modules/workspace.py — unchanged
except PROJECT_ROOT now resolves to apps/api, and a cleanup_abandoned_workspaces
helper was added (roadmap Phase 1: "Cleanup job (abandoned workspaces)").

Uploaded videos and generated artifacts must never use shared fixed filenames.
Each analysis run receives an isolated directory under ``runtime/analyses``.
"""

from __future__ import annotations

import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _runtime_root() -> Path:
    configured_root = os.getenv("CADENCE_RUNTIME_DIR")
    return Path(configured_root) if configured_root else PROJECT_ROOT / "runtime"


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
        return self.root / "professional_keypoints.npy"

    @property
    def user_keypoints(self) -> Path:
        return self.root / "user_keypoints.npy"

    @property
    def overlay(self) -> Path:
        return self.root / "overlay.mp4"


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

    Intended to run on a schedule (see apps/worker's cron job) so a
    crashed upload or an analysis nobody ever finished doesn't leak
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
