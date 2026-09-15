from __future__ import annotations


def _register(client, email="ada@example.com", password="correct-horse-battery"):
    return client.post(
        "/auth/register",
        json={"name": "Ada Lovelace", "email": email, "password": password, "confirm": password},
    )


def test_register_login_me_logout_flow(client):
    register_response = _register(client)
    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login", json={"email": "ada@example.com", "password": "correct-horse-battery"}
    )
    assert login_response.status_code == 200
    assert login_response.json()["email"] == "ada@example.com"
    assert "cadence_session" in login_response.cookies

    me_response = client.get("/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "ada@example.com"

    logout_response = client.post("/auth/logout")
    assert logout_response.status_code == 200

    me_after_logout = client.get("/auth/me")
    assert me_after_logout.status_code == 401


def test_me_without_session_is_unauthorized(client):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_login_with_wrong_password_is_rejected(client):
    _register(client)
    response = client.post("/auth/login", json={"email": "ada@example.com", "password": "wrong"})
    assert response.status_code == 401


def test_register_rejects_weak_password(client):
    response = client.post(
        "/auth/register",
        json={"name": "Ada", "email": "ada@example.com", "password": "short", "confirm": "short"},
    )
    assert response.status_code == 400
