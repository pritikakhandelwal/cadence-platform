from __future__ import annotations

from cadence_db import Analysis


def _register_and_login(client, email="ada@example.com", password="correct-horse-battery"):
    client.post(
        "/auth/register",
        json={"name": "Ada", "email": email, "password": password, "confirm": password},
    )
    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200


def _make_needs_dancer_pick_analysis(db_session, user_id: str) -> Analysis:
    """Simulates what detect_tracks_job would have written for an
    ambiguous (duo/mirror-like) clip -- there's no live worker in these
    tests, so this seeds the row directly rather than going through a
    real upload + job run (that's covered by
    apps/worker/tests/test_tasks_integration.py instead)."""

    analysis = Analysis(
        user_id=user_id,
        workspace_id="ws-test",
        status="needs_dancer_pick",
        pending_lock_data={
            "detections": [
                {"frame_idx": 0, "track_id": 1, "bbox": [0, 0, 10, 10], "confidence": 0.9},
                {"frame_idx": 0, "track_id": 2, "bbox": [20, 0, 30, 10], "confidence": 0.8},
            ],
            "fps": 30.0,
            "total_frames": 10,
            "tracks": [
                {"track_id": 1, "frame_count": 5, "mean_confidence": 0.9, "fragments": 1},
                {"track_id": 2, "frame_count": 5, "mean_confidence": 0.8, "fragments": 1},
            ],
        },
    )
    db_session.add(analysis)
    db_session.commit()
    return analysis


def test_upload_requires_authentication(client, tiny_mp4_bytes):
    response = client.post(
        "/analyses",
        files={
            "professional_video": ("pro.mp4", tiny_mp4_bytes, "video/mp4"),
            "user_video": ("user.mp4", tiny_mp4_bytes, "video/mp4"),
        },
    )
    assert response.status_code == 401


def test_upload_creates_a_persisted_queued_analysis(client, tiny_mp4_bytes):
    _register_and_login(client)

    response = client.post(
        "/analyses",
        files={
            "professional_video": ("pro.mp4", tiny_mp4_bytes, "video/mp4"),
            "user_video": ("user.mp4", tiny_mp4_bytes, "video/mp4"),
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "queued"
    analysis_id = body["analysis_id"]

    get_response = client.get(f"/analyses/{analysis_id}")
    assert get_response.status_code == 200
    result = get_response.json()
    assert result["analysis_id"] == analysis_id
    assert result["status"] == "queued"
    assert result["quality_gate"]["passed"] is False


def test_upload_enqueues_the_phase_2_detect_tracks_job(client, fake_queue, tiny_mp4_bytes):
    _register_and_login(client)

    response = client.post(
        "/analyses",
        files={
            "professional_video": ("pro.mp4", tiny_mp4_bytes, "video/mp4"),
            "user_video": ("user.mp4", tiny_mp4_bytes, "video/mp4"),
        },
    )
    assert response.status_code == 201
    analysis_id = response.json()["analysis_id"]

    assert len(fake_queue.enqueued) == 1
    job = fake_queue.enqueued[0]
    assert job["function"] == "detect_tracks_job"
    assert job["kwargs"]["analysis_id"] == analysis_id
    # locks onto the user's own upload, not the professional reference --
    # see docs/decisions.md
    assert job["kwargs"]["video_path"].endswith("user_upload.mp4")


def test_upload_rejects_invalid_video(client):
    _register_and_login(client)

    response = client.post(
        "/analyses",
        files={
            "professional_video": ("pro.mp4", b"not a real mp4", "video/mp4"),
            "user_video": ("user.mp4", b"not a real mp4", "video/mp4"),
        },
    )
    assert response.status_code == 400


def test_cannot_read_another_users_analysis(client, tiny_mp4_bytes):
    _register_and_login(client, email="ada@example.com")
    create_response = client.post(
        "/analyses",
        files={
            "professional_video": ("pro.mp4", tiny_mp4_bytes, "video/mp4"),
            "user_video": ("user.mp4", tiny_mp4_bytes, "video/mp4"),
        },
    )
    analysis_id = create_response.json()["analysis_id"]

    client.post("/auth/logout")
    _register_and_login(client, email="grace@example.com")

    response = client.get(f"/analyses/{analysis_id}")
    assert response.status_code == 404


def test_get_analysis_reports_needs_dancer_pick_with_person_count(client, db_session):
    _register_and_login(client)
    me = client.get("/auth/me").json()
    analysis = _make_needs_dancer_pick_analysis(db_session, me["id"])

    response = client.get(f"/analyses/{analysis.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "needs_dancer_pick"
    assert body["tracking"]["person_count"] == 2
    assert "candidate-tracks" in body["quality_gate"]["reasons"][0]


def test_candidate_tracks_lists_both_tracks(client, db_session):
    _register_and_login(client)
    me = client.get("/auth/me").json()
    analysis = _make_needs_dancer_pick_analysis(db_session, me["id"])

    response = client.get(f"/analyses/{analysis.id}/candidate-tracks")
    assert response.status_code == 200
    track_ids = {t["track_id"] for t in response.json()}
    assert track_ids == {1, 2}


def test_candidate_tracks_rejects_a_non_pending_analysis(client, tiny_mp4_bytes):
    _register_and_login(client)
    create_response = client.post(
        "/analyses",
        files={
            "professional_video": ("pro.mp4", tiny_mp4_bytes, "video/mp4"),
            "user_video": ("user.mp4", tiny_mp4_bytes, "video/mp4"),
        },
    )
    analysis_id = create_response.json()["analysis_id"]  # status is "queued", not needs_dancer_pick

    response = client.get(f"/analyses/{analysis_id}/candidate-tracks")
    assert response.status_code == 400


def test_lock_enqueues_extract_locked_pose_job_and_marks_running(client, db_session, fake_queue):
    _register_and_login(client)
    me = client.get("/auth/me").json()
    analysis = _make_needs_dancer_pick_analysis(db_session, me["id"])

    response = client.post(f"/analyses/{analysis.id}/lock", json={"track_id": 2})
    assert response.status_code == 202
    assert response.json()["status"] == "running"

    assert len(fake_queue.enqueued) == 1
    job = fake_queue.enqueued[0]
    assert job["function"] == "extract_locked_pose_job"
    assert job["kwargs"]["analysis_id"] == analysis.id
    assert job["kwargs"]["track_id"] == 2
    assert job["kwargs"]["fps"] == 30.0
    assert len(job["kwargs"]["detections"]) == 2


def test_lock_rejects_an_unknown_track_id(client, db_session):
    _register_and_login(client)
    me = client.get("/auth/me").json()
    analysis = _make_needs_dancer_pick_analysis(db_session, me["id"])

    response = client.post(f"/analyses/{analysis.id}/lock", json={"track_id": 999})
    assert response.status_code == 400


def test_lock_rejects_a_non_pending_analysis(client, tiny_mp4_bytes):
    _register_and_login(client)
    create_response = client.post(
        "/analyses",
        files={
            "professional_video": ("pro.mp4", tiny_mp4_bytes, "video/mp4"),
            "user_video": ("user.mp4", tiny_mp4_bytes, "video/mp4"),
        },
    )
    analysis_id = create_response.json()["analysis_id"]

    response = client.post(f"/analyses/{analysis_id}/lock", json={"track_id": 1})
    assert response.status_code == 400
