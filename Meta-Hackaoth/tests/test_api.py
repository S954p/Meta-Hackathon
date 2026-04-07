from __future__ import annotations

from fastapi.testclient import TestClient

from server.app import app


client = TestClient(app)


def test_tasks_endpoint_returns_required_tasks():
    r = client.get("/tasks")
    assert r.status_code == 200
    payload = r.json()
    assert "tasks" in payload
    task_ids = {t["task_id"] for t in payload["tasks"]}
    assert "easy_password_reset" in task_ids
    assert "medium_billing_missing_info" in task_ids
    assert "hard_technical_troubleshooting" in task_ids


def test_reset_rejects_invalid_task_id():
    r = client.post("/reset", json={"task_id": "invalid_task_name"})
    assert r.status_code == 400
    assert "Invalid task_id" in r.json().get("detail", "")


def test_state_get_works_after_reset():
    r = client.post("/reset", json={"task_id": "easy_password_reset", "seed": 1})
    assert r.status_code == 200
    episode_id = r.json()["episode_id"]

    state_response = client.get("/state", params={"episode_id": episode_id})
    assert state_response.status_code == 200
    state = state_response.json()["state"]
    assert state["task_id"] == "easy_password_reset"
    assert "ticket" in state

