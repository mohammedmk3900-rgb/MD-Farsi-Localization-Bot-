from __future__ import annotations

from app.integrations.paratranz import ParaTranzConfig, ParaTranzError, ParaTranzIntegration


def test_paratranz_stats_aggregate_documented_file_payloads(monkeypatch):
    integration = ParaTranzIntegration(ParaTranzConfig(19621, "https://example.test"))
    payloads = {
        "projects/19621": {"data": {"id": 19621, "members": 2}},
        "projects/19621/files": {"data": [
            {"name": "a.yml", "total": 12, "translated": 7, "reviewed": 3, "words": 100},
            {"name": "b.yml", "total": 8, "translated": 4, "reviewed": 2, "words": 50},
        ]},
    }
    monkeypatch.setattr(integration, "_get", lambda path: payloads[path])
    stats = integration.stats()
    assert stats.project_id == 19621
    assert stats.strings_total == 20
    assert stats.translated == 11
    assert stats.reviewed == 5
    assert stats.words_total == 150
    assert stats.files == 2
    assert stats.members == 2


def test_paratranz_terms(monkeypatch):
    integration = ParaTranzIntegration(ParaTranzConfig(19621, "https://example.test"))
    monkeypatch.setattr(
        integration,
        "_get",
        lambda path: {"data": {"terms": [{"id": 1, "source": "Faction", "target": "اتحاد"}], "pageCount": 1}},
    )
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


def test_paratranz_normalizes_bearer_prefixed_token(monkeypatch):
    from unittest.mock import patch
    from urllib.request import Request

    integration = ParaTranzIntegration(
        ParaTranzConfig(19621, "https://example.test"),
        token="Bearer example-token",
    )
    seen = {}

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return b'{"id":19621}'

    def fake_urlopen(request, timeout):
        seen["authorization"] = request.get_header("Authorization")
        return Response()

    monkeypatch.setattr("app.integrations.paratranz.urlopen", fake_urlopen)
    assert integration._get("projects/19621") == {"id": 19621}
    assert seen["authorization"] == "example-token"


def test_paratranz_rejects_empty_file_snapshot(monkeypatch):
    integration = ParaTranzIntegration(ParaTranzConfig(19621, "https://example.test"))
    payloads = {
        "projects/19621": {"id": 19621, "members": 2},
        "projects/19621/files": [],
    }
    monkeypatch.setattr(integration, "_get", lambda path: payloads[path])
    try:
        integration.stats()
    except ParaTranzError as exc:
        assert "no project files" in str(exc)
    else:
        assert False, "expected invalid empty snapshot to be rejected"


from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.persistence.store import Store
from app.services.application import GenesisApplication
from app.services.scheduling import ScheduledSyncRunner


class FakeSyncSource:
    def __init__(self, *, project_id=19621, terms=None, fail=False):
        self.config = SimpleNamespace(project_id=project_id)
        self.terms = terms if terms is not None else [{"source": "Stability", "target": "ثبات"}]
        self.fail = fail

    def stats(self):
        if self.fail:
            raise RuntimeError("upstream timeout")
        return SimpleNamespace(
            project_id=self.config.project_id, strings_total=100,
            translated=25, reviewed=20, files=4, members=3,
        )

    def glossary(self):
        return self.terms


def _make_app(tmp_path):
    app = GenesisApplication(Store(tmp_path / "genesis.db"))
    app.initialize()
    return app


def test_sync_persists_snapshot_run_and_audit(tmp_path):
    app = _make_app(tmp_path)
    result = app.sync.project(app, FakeSyncSource())
    assert result["project_id"] == 19621
    assert result["glossary_terms"] == 1
    assert app.glossary.find("stability")[0].target == "ثبات"
    assert app.store.latest_glossary_snapshot(19621)[0]["source"] == "Stability"
    assert app.store.counts()["sync_runs"] == 1
    assert app.store.events()[0]["event_type"] == "paratranz.sync"


def test_scheduler_runs_sync_and_sets_next_interval(tmp_path):
    app = _make_app(tmp_path)
    runner = ScheduledSyncRunner(app, FakeSyncSource(), interval_seconds=120)
    now = datetime(2026, 10, 11, tzinfo=timezone.utc)
    runner.register(now.isoformat())
    assert runner.run_once(now) is not None
    job = app.store.scheduler_job(runner.JOB_ID)
    assert job["status"] == "pending"
    assert job["next_run_at"] is not None
    assert job["run_count"] == 1
    assert runner.run_once(now) is None


def test_scheduler_respects_future_due_time(tmp_path):
    app = _make_app(tmp_path)
    runner = ScheduledSyncRunner(app, FakeSyncSource())
    future = datetime(2026, 10, 12, tzinfo=timezone.utc)
    runner.register(future.isoformat())
    assert runner.run_once(datetime(2026, 10, 11, tzinfo=timezone.utc)) is None
    assert app.store.counts()["sync_runs"] == 0


def test_scheduler_failure_records_retry_and_persistent_alert(tmp_path):
    app = _make_app(tmp_path)
    runner = ScheduledSyncRunner(app, FakeSyncSource(fail=True))
    runner.register()
    with pytest.raises(RuntimeError, match="upstream timeout"):
        runner.run_once()
    job = app.store.scheduler_job(runner.JOB_ID)
    assert job["status"] == "pending"
    assert job["failure_count"] == 1
    assert "upstream timeout" in job["last_error"]
    assert any(alert["code"] == "PARATRANZ_SYNC_FAILED" for alert in app.alerts.active())
    assert app.store.counts()["sync_runs"] == 1


def test_empty_upstream_glossary_preserves_previous_snapshot(tmp_path):
    app = _make_app(tmp_path)
    app.sync.project(app, FakeSyncSource())
    before = app.store.latest_glossary_snapshot(19621)
    with pytest.raises(Exception, match="glossary is empty"):
        app.sync.project(app, FakeSyncSource(terms=[]))
    assert app.store.latest_glossary_snapshot(19621) == before
    assert app.glossary.find("Stability")[0].target == "ثبات"


from app.integrations.discord import DiscordActor, DiscordCommandAdapter, DiscordCommandError, DiscordCommandGateway


def test_discord_adapter_runs_sync_and_audits_command(tmp_path):
    app = _make_app(tmp_path)
    adapter = DiscordCommandAdapter(DiscordCommandGateway(app))
    result = adapter.dispatch(DiscordActor("manager-1", ("project_manager",)), "sync", integration=FakeSyncSource())
    assert result["glossary_terms"] == 1
    assert any(event["event_type"] == "discord.command" for event in app.store.events())


def test_discord_adapter_denies_sync_to_translator(tmp_path):
    app = _make_app(tmp_path)
    adapter = DiscordCommandAdapter(DiscordCommandGateway(app))
    with pytest.raises(DiscordCommandError, match="permission denied"):
        adapter.dispatch(DiscordActor("translator-1", ("translator",)), "sync", integration=FakeSyncSource())
    assert app.store.counts()["sync_runs"] == 0


def test_failed_atomic_sync_does_not_replace_glossary_or_snapshot(tmp_path, monkeypatch):
    app = _make_app(tmp_path)
    source = FakeSyncSource()

    def fail_commit(*args, **kwargs):
        raise RuntimeError("database commit failed")

    monkeypatch.setattr(app.store, "record_sync_success", fail_commit)
    with pytest.raises(RuntimeError, match="database commit failed"):
        app.sync.project(app, source)

    assert app.store.latest_glossary_snapshot(19621) is None
    assert app.glossary.all() == []
    runs = app.store.counts()["sync_runs"]
    assert runs == 1
    assert app.store.events()[0]["event_type"] == "paratranz.sync.failed"
