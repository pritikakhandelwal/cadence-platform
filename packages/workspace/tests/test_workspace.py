from __future__ import annotations

import os
import time

from cadence_workspace import (
    cleanup_abandoned_workspaces,
    create_analysis_workspace,
    remove_analysis_workspace,
    workspace_for,
)


def test_each_workspace_gets_a_unique_isolated_directory(tmp_path):
    analyses_dir = tmp_path / "analyses"
    ws1 = create_analysis_workspace(base_dir=analyses_dir)
    ws2 = create_analysis_workspace(base_dir=analyses_dir)

    assert ws1.run_id != ws2.run_id
    assert ws1.root != ws2.root
    assert ws1.root.is_dir()
    assert ws1.professional_upload.parent == ws1.root


def test_remove_workspace_deletes_its_directory(tmp_path, monkeypatch):
    monkeypatch.setenv("CADENCE_RUNTIME_DIR", str(tmp_path / "runtime"))
    ws = create_analysis_workspace()
    assert ws.root.is_dir()

    remove_analysis_workspace(ws)
    assert not ws.root.exists()


def test_remove_workspace_refuses_paths_outside_analyses_dir(tmp_path):
    from cadence_workspace import AnalysisWorkspace

    outside = tmp_path / "not-a-workspace"
    outside.mkdir()
    fake_workspace = AnalysisWorkspace(run_id="x", root=outside)

    try:
        remove_analysis_workspace(fake_workspace)
    except ValueError:
        pass
    else:
        raise AssertionError("expected a ValueError for a path outside the analyses dir")
    assert outside.exists()


def test_cleanup_removes_only_old_workspaces(tmp_path):
    analyses_dir = tmp_path / "analyses"
    old_ws = create_analysis_workspace(base_dir=analyses_dir)
    new_ws = create_analysis_workspace(base_dir=analyses_dir)

    old_time = time.time() - 48 * 3600
    os.utime(old_ws.root, (old_time, old_time))

    removed = cleanup_abandoned_workspaces(max_age_hours=24, base_dir=analyses_dir)

    assert old_ws.run_id in removed
    assert new_ws.run_id not in removed
    assert not old_ws.root.exists()
    assert new_ws.root.exists()


def test_workspace_for_reconstructs_an_existing_workspace(tmp_path):
    analyses_dir = tmp_path / "analyses"
    original = create_analysis_workspace(base_dir=analyses_dir)

    reconstructed = workspace_for(original.run_id, base_dir=analyses_dir)

    assert reconstructed.root == original.root
    assert reconstructed.user_upload == original.user_upload
