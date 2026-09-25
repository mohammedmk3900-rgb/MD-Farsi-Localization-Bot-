from __future__ import annotations

import json

from app.integrations.paratranz import ParaTranzConfig, ParaTranzError, ParaTranzIntegration
from app.services.command_center import CommandCenterService


def test_paratranz_stats_from_project_payload(monkeypatch):
    integration = ParaTranzIntegration(ParaTranzConfig(19621, "https://example.test"))
    payload = {
        "data": {
            "stats": {"words": 100, "strings": 20, "translated": 7, "reviewed": 3},
            "files": 4,
            "members": 2,
        }
    }
    monkeypatch.setattr(integration, "_get", lambda path: payload)
    assert integration.stats().translated == 7
    assert integration.stats().reviewed == 3
    assert integration.stats().files == 4


def test_paratranz_terms(monkeypatch):
    integration = ParaTranzIntegration(ParaTranzConfig(19621, "https://example.test"))
    monkeypatch.setattr(integration, "_get", lambda path: {"data": {"terms": [{"source": "Faction", "target": "اتحاد"}]}})
    assert integration.glossary()[0]["target"] == "اتحاد"


def test_paratranz_errors_are_wrapped(monkeypatch):
    integration = ParaTranzIntegration(ParaTranzConfig(19621, "https://example.test"))
    def broken(path):
        raise ValueError("bad json")
    monkeypatch.setattr(integration, "_get", broken)
    try:
        integration.stats()
    except ValueError:
        assert False, "raw transport error leaked"
    except ParaTranzError:
        pass
    else:
        assert False, "expected ParaTranzError"
