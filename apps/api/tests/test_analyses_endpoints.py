from __future__ import annotations


def _register_and_login(client, email="ada@example.com", password="correct-horse-battery"):
    client.post(
        "/auth/register",
        json={"name": "Ada", "email": email, "password": password, "confirm": password},
    )
    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200


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
