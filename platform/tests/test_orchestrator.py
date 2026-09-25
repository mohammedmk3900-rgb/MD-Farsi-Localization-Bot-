from __future__ import annotations

from unittest.mock import patch

from app.orchestrator import execute


def test_full_run_calls_each_operation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with (
        patch("app.orchestrator.jobs.sync", return_value={"project": {"strings_total": 10}}) as sync,
        patch("app.orchestrator.jobs.glossary_sync", return_value={"count": 1}) as glossary,
        patch("app.orchestrator.jobs.audit", return_value={"channels": 1}) as audit,
        patch("app.orchestrator.jobs.health", return_value={"status": "healthy"}) as health,
        patch("app.orchestrator.jobs.report", return_value={"period": "daily"}) as report,
    ):
        result = execute(daily=True, weekly=True)
    assert result["status"] == "ok"
    assert all(job["status"] == "ok" for job in result["jobs"].values())
    sync.assert_called_once()
    glossary.assert_called_once()
    audit.assert_called_once()
    health.assert_called_once()
    assert report.call_count == 2
    assert (tmp_path / "data" / "last_run.json").exists()


def test_invalid_project_blocks_reports_but_other_jobs_continue(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with (
        patch("app.orchestrator.jobs.sync", side_effect=ValueError("invalid API response")),
        patch("app.orchestrator.jobs.glossary_sync", return_value={"count": 1}),
        patch("app.orchestrator.jobs.audit", return_value={"channels": 1}),
        patch("app.orchestrator.jobs.health", return_value={"status": "degraded"}),
        patch("app.orchestrator.jobs.report") as report,
    ):
        result = execute(daily=True)
    assert result["status"] == "failed"
    assert result["jobs"]["sync"]["error_type"] == "ValueError"
    assert result["jobs"]["daily_report"]["status"] == "skipped"
    assert result["jobs"]["discord_audit"]["status"] == "ok"
    report.assert_not_called()


def test_public_run_summary_excludes_discord_identifiers(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with (
        patch("app.orchestrator.jobs.sync", return_value={"project": {"project_id": 19621}}),
        patch("app.orchestrator.jobs.glossary_sync", return_value={"count": 1}),
        patch("app.orchestrator.jobs.audit", return_value={
            "server": {"channels": 35, "roles": 12, "categories": 9},
            "channels": [{"id": "PRIVATE_CHANNEL_ID"}],
            "roles": [{"id": "PRIVATE_ROLE_ID"}],
        }),
        patch("app.orchestrator.jobs.health", return_value={"status": "healthy"}),
    ):
        result = execute()
    public_json = (tmp_path / "data" / "last_run.json").read_text(encoding="utf-8")
    assert "PRIVATE_CHANNEL_ID" not in public_json
    assert "PRIVATE_ROLE_ID" not in public_json
    assert result["jobs"]["discord_audit"]["result"]["channels"] == 35
