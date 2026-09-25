from __future__ import annotations

from unittest.mock import Mock, patch

import httpx

import pytest

from app.config import Settings
from app.integrations.paratranz import ParaTranzClient


def test_rejects_empty_paratranz_response():
    settings = Settings(paratranz_token="test-token")
    response = Mock()
    response.json.return_value = {}
    response.raise_for_status.return_value = None
    client = Mock()
    client.get.return_value = response
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=None)
    with patch("app.integrations.paratranz.httpx.Client", return_value=client):
        with pytest.raises(ValueError, match="missing project metrics"):
            ParaTranzClient(settings).project_snapshot()


def test_rejects_zeroed_paratranz_response():
    settings = Settings(paratranz_token="test-token")
    response = Mock()
    response.json.return_value = {
        "wordCount": 0, "stringCount": 0, "translated": 0,
        "reviewed": 0, "fileCount": 0, "memberCount": 0,
    }
    response.raise_for_status.return_value = None
    client = Mock()
    client.get.return_value = response
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=None)
    with patch("app.integrations.paratranz.httpx.Client", return_value=client):
        with pytest.raises(ValueError, match="empty project snapshot"):
            ParaTranzClient(settings).project_snapshot()


def test_accepts_valid_paratranz_response():
    settings = Settings(paratranz_token="test-token")
    response = Mock()
    response.json.return_value = {
        "wordCount": 1000, "stringCount": 100,
        "translated": 20, "reviewed": 10,
        "fileCount": 2, "memberCount": 3,
    }
    response.raise_for_status.return_value = None
    client = Mock()
    client.get.return_value = response
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=None)
    with patch("app.integrations.paratranz.httpx.Client", return_value=client):
        snapshot = ParaTranzClient(settings).project_snapshot()
    assert snapshot.strings_total == 100
    assert snapshot.translated == 20


def test_uses_bearer_authorization():
    settings = Settings(paratranz_token="abc123")
    response = Mock()
    response.json.return_value = {
        "wordCount": 1000, "stringCount": 100,
        "translated": 20, "reviewed": 10,
        "fileCount": 2, "memberCount": 3,
    }
    response.raise_for_status.return_value = None
    client = Mock()
    client.get.return_value = response
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=None)
    with patch("app.integrations.paratranz.httpx.Client", return_value=client) as factory:
        ParaTranzClient(settings).project_snapshot()
    headers = factory.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer abc123"


def test_preserves_existing_bearer_authorization():
    settings = Settings(paratranz_token="Bearer abc123")
    response = Mock()
    response.json.return_value = {
        "wordCount": 1000, "stringCount": 100,
        "translated": 20, "reviewed": 10,
        "fileCount": 2, "memberCount": 3,
    }
    response.raise_for_status.return_value = None
    client = Mock()
    client.get.return_value = response
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=None)
    with patch("app.integrations.paratranz.httpx.Client", return_value=client) as factory:
        ParaTranzClient(settings).project_snapshot()
    assert factory.call_args.kwargs["headers"]["Authorization"] == "Bearer abc123"
