from __future__ import annotations

from unittest.mock import patch

import pytest

from app.config import Settings
from app.integrations.paratranz import ParaTranzClient, ParaTranzDataError


def make_client(project, files, members=None):
    settings = Settings(paratranz_token="test-token", paratranz_project_id=19621)
    def get_json(path, *, params=None):
        if path == "projects/19621":
            return project
        if path == "projects/19621/files":
            return files
        if path == "projects/19621/members" and members is not None:
            return members
        raise AssertionError(f"Unexpected API path: {path}")
    client = ParaTranzClient(settings)
    client.api.get_json = get_json
    return client


def test_rejects_empty_project_file_response():
    client = make_client({"id": 19621}, [])
    with pytest.raises(ParaTranzDataError, match="no project files"):
        client.project_snapshot()


def test_rejects_zeroed_project_counters():
    client = make_client(
        {"id": 19621, "members": 0},
        [{"name": "empty.yml", "total": 0, "translated": 0, "reviewed": 0, "words": 0}],
    )
    with pytest.raises(ParaTranzDataError, match="no strings"):
        client.project_snapshot()


def test_accepts_aggregated_file_metrics():
    client = make_client(
        {"id": 19621, "members": 3},
        [
            {"name": "a.yml", "total": 60, "translated": 20, "reviewed": 10, "words": 500},
            {"name": "b.yml", "total": 40, "translated": 10, "reviewed": 5, "words": 300},
        ],
    )
    snapshot = client.project_snapshot()
    assert snapshot.project_id == 19621
    assert snapshot.strings_total == 100
    assert snapshot.words_total == 800
    assert snapshot.translated == 30
    assert snapshot.reviewed == 15
    assert snapshot.files == 2
    assert snapshot.members == 3


def test_rejects_response_for_wrong_project_id():
    client = make_client(
        {"id": 999, "members": 3},
        [{"name": "a.yml", "total": 10, "translated": 2, "reviewed": 1, "words": 50}],
    )
    with pytest.raises(ParaTranzDataError, match="different project"):
        client.project_snapshot()


def test_members_fallback_is_used_when_project_omits_count():
    client = make_client(
        {"id": 19621},
        [{"name": "a.yml", "total": 10, "translated": 2, "reviewed": 1, "words": 50}],
        [{"id": 1}, {"id": 2}],
    )
    snapshot = client.project_snapshot()
    assert snapshot.members == 2
