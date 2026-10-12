from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.integrations.paratranz import (
    ParaTranzAPI,
    ParaTranzAPIError,
    ParaTranzClient,
    ParaTranzDataError,
)
from app.integrations.paratranz_terms import ParaTranzTerms


class FakeResponse:
    def __init__(self, payload=None, status_code=200, headers=None):
        self.payload = payload
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


class FakeHttpClient:
    responses = {}
    requests = []

    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.__class__.requests.append({"kwargs": kwargs, "get": []})

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url, params=None):
        self.__class__.requests[-1]["get"].append({"url": url, "params": params})
        key = url
        response = self.responses.get(key)
        if isinstance(response, list):
            response = response.pop(0)
        if response is None:
            raise AssertionError(f"Unexpected URL: {url}")
        return response


@pytest.fixture(autouse=True)
def reset_fake_http():
    FakeHttpClient.responses = {}
    FakeHttpClient.requests = []
    yield
    FakeHttpClient.responses = {}
    FakeHttpClient.requests = []


def settings(**overrides):
    values = {
        "paratranz_token": "test-token",
        "paratranz_project_id": 19621,
        "paratranz_base_url": "https://paratranz.cn/api",
        "paratranz_timeout_seconds": 20.0,
        "paratranz_max_retries": 3,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def configure_project(*, project=None, files=None, members=None):
    base = "https://paratranz.cn/api/projects/19621"
    FakeHttpClient.responses[base] = FakeResponse(
        project if project is not None else {"id": 19621, "name": "Millennium Dawn", "members": 7}
    )
    FakeHttpClient.responses[f"{base}/files"] = FakeResponse(
        files if files is not None else [
            {"name": "a.yml", "total": 100, "translated": 25, "reviewed": 10, "words": 500},
            {"name": "b.yml", "total": 40, "translated": 15, "reviewed": 8, "words": 200},
        ]
    )
    if members is not None:
        FakeHttpClient.responses[f"{base}/members"] = members


def test_project_snapshot_aggregates_documented_file_metrics():
    configure_project()
    with patch("app.integrations.paratranz.httpx.Client", FakeHttpClient):
        snapshot = ParaTranzClient(settings()).project_snapshot()

    assert snapshot.project_id == 19621
    assert snapshot.words_total == 700
    assert snapshot.strings_total == 140
    assert snapshot.translated == 40
    assert snapshot.reviewed == 18
    assert snapshot.files == 2
    assert snapshot.members == 7


def test_para_tranz_uses_raw_authorization_token_per_api_docs():
    configure_project()
    with patch("app.integrations.paratranz.httpx.Client", FakeHttpClient):
        ParaTranzClient(settings(paratranz_token="Bearer pasted-token")).project_snapshot()

    assert FakeHttpClient.requests[0]["kwargs"]["headers"]["Authorization"] == "pasted-token"


def test_rejects_missing_file_metrics_instead_of_fabricating_zeroes():
    configure_project(files=[
        {"name": "broken.yml", "total": 10, "translated": 2, "words": 30}
    ])
    with patch("app.integrations.paratranz.httpx.Client", FakeHttpClient):
        with pytest.raises(ParaTranzDataError, match="broken.yml.*reviewed"):
            ParaTranzClient(settings()).project_snapshot()


def test_rejects_empty_files_response():
    configure_project(files=[])
    with patch("app.integrations.paratranz.httpx.Client", FakeHttpClient):
        with pytest.raises(ParaTranzDataError, match="no project files"):
            ParaTranzClient(settings()).project_snapshot()


def test_falls_back_to_paginated_members_endpoint():
    configure_project(project={"id": 19621, "name": "Millennium Dawn"})
    base = "https://paratranz.cn/api/projects/19621/members"
    FakeHttpClient.responses[base] = FakeResponse({"results": [{"id": 1}, {"id": 2}], "pageCount": 2})
    FakeHttpClient.responses[base] = [
        FakeResponse({"results": [{"id": 1}, {"id": 2}], "pageCount": 2}),
        FakeResponse({"results": [{"id": 3}], "pageCount": 2}),
    ]

    with patch("app.integrations.paratranz.httpx.Client", FakeHttpClient):
        snapshot = ParaTranzClient(settings()).project_snapshot()

    assert snapshot.members == 3


def test_retries_rate_limit_and_honors_retry_after():
    FakeHttpClient.responses["https://paratranz.cn/api/projects/19621"] = [
        FakeResponse({"message": "slow down"}, status_code=429, headers={"Retry-After": "0"}),
        FakeResponse({"id": 19621, "name": "Millennium Dawn", "members": 7}),
    ]
    with patch("app.integrations.paratranz.httpx.Client", FakeHttpClient), patch(
        "app.integrations.paratranz.time.sleep"
    ) as sleep:
        payload = ParaTranzAPI("token", max_retries=1).get_json("projects/19621")

    assert payload["id"] == 19621
    sleep.assert_called_once_with(0.0)


def test_surfaces_safe_http_error_metadata():
    FakeHttpClient.responses["https://paratranz.cn/api/projects/19621"] = FakeResponse(
        {"message": "token invalid", "code": 40101}, status_code=401
    )
    with patch("app.integrations.paratranz.httpx.Client", FakeHttpClient):
        with pytest.raises(ParaTranzAPIError) as error:
            ParaTranzAPI("secret-token").get_json("projects/19621")

    assert error.value.status_code == 401
    assert error.value.api_code == 40101


def test_terms_adapter_handles_wrapped_paginated_payload():
    FakeHttpClient.responses["https://paratranz.cn/api/projects/19621/terms"] = FakeResponse(
        {"data": {"terms": [{"id": 1, "term": "Faction", "translation": "اتحاد"}], "pageCount": 1}}
    )
    with patch("app.integrations.paratranz.httpx.Client", FakeHttpClient):
        terms = ParaTranzTerms(19621, "token").list(page=1, page_size=50)

    assert terms == [{"id": 1, "term": "Faction", "translation": "اتحاد"}]


def test_unknown_successful_list_shape_is_not_mistaken_for_empty_list():
    FakeHttpClient.responses["https://paratranz.cn/api/projects/19621/terms"] = FakeResponse(
        {"unexpected": "shape"}
    )
    with patch("app.integrations.paratranz.httpx.Client", FakeHttpClient):
        with pytest.raises(ParaTranzDataError, match="recognized collection"):
            ParaTranzTerms(19621, "token").list()
