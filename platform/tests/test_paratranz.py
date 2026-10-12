from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.integrations.paratranz import ParaTranzClient


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeHttpClient:
    def __init__(self, *args, **kwargs):
        self.responses = {
            "https://paratranz.cn/api/projects/19621": {
                "id": 19621,
                "name": "Millennium Dawn: Farsi Localization",
                "members": 7,
            },
            "https://paratranz.cn/api/projects/19621/files": [
                {"name": "a.yml", "total": 100, "translated": 25, "reviewed": 10, "words": 500},
                {"name": "b.yml", "total": 40, "translated": 15, "reviewed": 8, "words": 200},
            ],
        }

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url):
        return FakeResponse(self.responses[url])


def test_project_snapshot_aggregates_documented_file_metrics():
    settings = SimpleNamespace(paratranz_token="test-token", paratranz_project_id=19621)

    with patch("app.integrations.paratranz.httpx.Client", FakeHttpClient):
        snapshot = ParaTranzClient(settings).project_snapshot()

    assert snapshot.project_id == 19621
    assert snapshot.words_total == 700
    assert snapshot.strings_total == 140
    assert snapshot.translated == 40
    assert snapshot.reviewed == 18
    assert snapshot.files == 2
    assert snapshot.members == 7


def test_project_snapshot_rejects_missing_file_metrics():
    settings = SimpleNamespace(paratranz_token="test-token", paratranz_project_id=19621)

    class MissingMetricsClient(FakeHttpClient):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.responses["https://paratranz.cn/api/projects/19621/files"] = [
                {"name": "broken.yml", "total": 10, "translated": 2, "words": 30}
            ]

    with patch("app.integrations.paratranz.httpx.Client", MissingMetricsClient):
        with pytest.raises(ValueError, match="broken.yml.*reviewed"):
            ParaTranzClient(settings).project_snapshot()


def test_project_snapshot_rejects_missing_project_member_count():
    settings = SimpleNamespace(paratranz_token="test-token", paratranz_project_id=19621)

    class MissingMembersClient(FakeHttpClient):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.responses["https://paratranz.cn/api/projects/19621"].pop("members")

    with patch("app.integrations.paratranz.httpx.Client", MissingMembersClient):
        with pytest.raises(ValueError, match="missing member count"):
            ParaTranzClient(settings).project_snapshot()
