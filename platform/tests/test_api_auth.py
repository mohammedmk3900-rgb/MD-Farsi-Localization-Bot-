from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.main import app


def test_project_sync_requires_management_token():
    client = TestClient(app)
    with patch("app.api.main.application.context.settings.api_token", "secret-test-token"):
        assert client.post("/api/v1/project/sync").status_code == 403
        assert client.post("/api/v1/project/sync", headers={"Authorization": "Bearer wrong"}).status_code == 403


def test_project_sync_with_authorized_token():
    client = TestClient(app)
    with (
        patch("app.api.main.application.context.settings.api_token", "secret-test-token"),
        patch("app.api.main.sync_project", return_value={"project_id": 19621}),
    ):
        response = client.post(
            "/api/v1/project/sync",
            headers={"Authorization": "Bearer secret-test-token"},
        )
    assert response.status_code == 200
    assert response.json()["project_id"] == 19621
