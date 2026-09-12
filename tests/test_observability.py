"""
Homework 2 authentication tests. They run offline, with no dependency on Langfuse, Docker, or model key

The TestClient is used without its context manager, so the app lifespan
(and therefore setup_tracing) never runs. Both requests below are rejected
by create_session or _authorize before any agent code executes.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from server import app as server_app

client = TestClient(server_app.app)


def test_create_session_rejects_role_that_differs_from_database(world: dict) -> None:
    server_app._SESSIONS.clear()
    # User 1 is a shopper in the seeded world; claiming merchant must fail.
    response = client.post("/sessions", json={"user_id": 1, "role": "merchant"})
    assert response.status_code == 403
    assert server_app._SESSIONS == {}


def test_token_for_one_session_cannot_authorize_another(world: dict) -> None:
    server_app._SESSIONS.clear()
    first = client.post("/sessions", json={"user_id": 1, "role": "shopper"}).json()
    second = client.post("/sessions", json={"user_id": 2, "role": "shopper"}).json()

    response = client.post(
        f"/sessions/{second['session_id']}/messages",
        json={"message": "Show my recent orders."},
        headers={"Authorization": f"Bearer {first['token']}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "token is for another session"