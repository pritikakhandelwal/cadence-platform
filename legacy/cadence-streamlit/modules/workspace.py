"""Per-analysis file workspaces.

Uploaded videos and generated artifacts must never use shared fixed filenames.
Each analysis run receives an isolated directory under ``runtime/analyses``.
"""

from __future__ import annotations

import os
import shutil
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
    def professional_skeleton_raw(self) -> Path:
        return self.root / "professional_skeleton_raw.mp4"

    @property
    def user_skeleton_raw(self) -> Path:
        return self.root / "user_skeleton_raw.mp4"

    @property
    def professional_skeleton(self) -> Path:
        return self.root / "professional_skeleton.mp4"

    @property
    def user_skeleton(self) -> Path:
        return self.root / "user_skeleton.mp4"

    @property
    def overlay_raw(self) -> Path:
        return self.root / "overlay_raw.mp4"

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
