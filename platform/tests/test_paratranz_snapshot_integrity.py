from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from app.config import Settings
from app.integrations.paratranz import ParaTranzClient


PROJECT_URL = "https://paratranz.cn/api/projects/19621"
FILES_URL = f"{PROJECT_URL}/files"


def response(payload):
    result = Mock()
    result.json.return_value = payload
    result.raise_for_status.return_value = None
    return result


def client_for(project_payload, files_payload):
    client = Mock()
    payloads = {
        PROJECT_URL: project_payload,
        FILES_URL: files_payload,
    }
    client.get.side_effect = lambda url: response(payloads[url])
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=None)
    return client


def valid_project():
    return {"id": 19621, "name": "Millennium Dawn: Farsi Localization", "members": 3}


def valid_files():
    return [
        {"name": "a.yml", "total": 60, "translated": 12, "reviewed": 6, "words": 600},
        {"name": "b.yml", "total": 40, "translated": 8, "reviewed": 4, "words": 400},
    ]


def test_rejects_empty_paratranz_response():
    settings = Settings(paratranz_token="test-token")
    client = client_for({}, [])
    with patch("app.integrations.paratranz.httpx.Client", return_value=client):
        with pytest.raises(ValueError, match="empty project snapshot"):
            ParaTranzClient(settings).project_snapshot()


def test_rejects_zeroed_paratranz_response():
    settings = Settings(paratranz_token="test-token")
    project = {"id": 19621, "name": "empty project", "members": 0}
    files = [{"name": "empty.yml", "total": 0, "translated": 0, "reviewed": 0, "words": 0}]
    client = client_for(project, files)
    with patch("app.integrations.paratranz.httpx.Client", return_value=client):
        with pytest.raises(ValueError, match="empty project snapshot"):
            ParaTranzClient(settings).project_snapshot()


def test_accepts_valid_paratranz_response_and_aggregates_file_metrics():
    settings = Settings(paratranz_token="test-token")
    client = client_for(valid_project(), valid_files())
    with patch("app.integrations.paratranz.httpx.Client", return_value=client):
        snapshot = ParaTranzClient(settings).project_snapshot()

    assert snapshot.project_id == 19621
    assert snapshot.strings_total == 100
    assert snapshot.words_total == 1000
    assert snapshot.translated == 20
    assert snapshot.reviewed == 10
    assert snapshot.files == 2
    assert snapshot.members == 3


def test_uses_bearer_authorization():
    settings = Settings(paratranz_token="abc123")
    client = client_for(valid_project(), valid_files())
    with patch("app.integrations.paratranz.httpx.Client", return_value=client) as factory:
        ParaTranzClient(settings).project_snapshot()
    assert factory.call_args.kwargs["headers"]["Authorization"] == "Bearer abc123"


def test_preserves_existing_bearer_authorization():
    settings = Settings(paratranz_token="Bearer abc123")
    client = client_for(valid_project(), valid_files())
    with patch("app.integrations.paratranz.httpx.Client", return_value=client) as factory:
        ParaTranzClient(settings).project_snapshot()
    assert factory.call_args.kwargs["headers"]["Authorization"] == "Bearer abc123"


def test_rejects_file_missing_a_required_counter():
    settings = Settings(paratranz_token="test-token")
    files = [{"name": "broken.yml", "total": 10, "translated": 2, "words": 30}]
    client = client_for(valid_project(), files)
    with patch("app.integrations.paratranz.httpx.Client", return_value=client):
        with pytest.raises(ValueError, match="broken.yml.*reviewed"):
            ParaTranzClient(settings).project_snapshot()


def test_rejects_project_without_member_count():
    settings = Settings(paratranz_token="test-token")
    project = {"id": 19621, "name": "missing members"}
    client = client_for(project, valid_files())
    with patch("app.integrations.paratranz.httpx.Client", return_value=client):
        with pytest.raises(ValueError, match="missing member count"):
            ParaTranzClient(settings).project_snapshot()
