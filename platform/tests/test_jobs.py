from types import SimpleNamespace
from unittest.mock import patch

from app.services import jobs


class FakeSnapshot:
    def model_dump(self, mode="json"):
        return {
            "project": {
                "project_id": 19621,
                "translated": 10,
                "reviewed": 5,
                "strings_total": 100,
            }
        }


class FakeAutomation:
    def __init__(self):
        self.calls = []

    def publish_project(self):
        self.calls.append("project")
        raise RuntimeError("discord unavailable")

    def publish_intelligence(self):
        self.calls.append("intelligence")
        return {"published": False, "reason": "artifact_missing"}

    def publish_manager_digest(self):
        self.calls.append("manager_digest")
        return {"published": False, "reason": "missing_project_or_channel"}


def test_sync_survives_automation_delivery_failure():
    events = []
    application = SimpleNamespace(
        context=SimpleNamespace(
            settings=SimpleNamespace(),
            database=SimpleNamespace(),
        )
    )
    application.record = lambda event_type, payload: events.append((event_type, payload))

    command_center = SimpleNamespace(collect=lambda: FakeSnapshot())
    automation = FakeAutomation()

    with (
        patch.object(jobs, "application", application),
        patch.object(jobs, "CommandCenter", return_value=command_center),
        patch.object(jobs, "Automation", return_value=automation),
    ):
        result = jobs.sync()

    assert result["project"]["project_id"] == 19621
    assert automation.calls == ["project", "intelligence", "manager_digest"]
    assert ("automation.delivery_failed", {
        "operation": "project",
        "error_type": "RuntimeError",
    }) in events
    assert ("automation.sync", {
        "status": "degraded",
        "operations": 3,
        "failed_operations": 1,
    }) in events


def test_health_notification_failure_does_not_break_health_result():
    events = []
    settings = SimpleNamespace(channel_health="health")
    application = SimpleNamespace(
        context=SimpleNamespace(settings=settings),
    )
    application.record = lambda event_type, payload: events.append((event_type, payload))

    health_result = SimpleNamespace(
        model_dump=lambda mode="json": {
            "status": "degraded",
            "paratranz": True,
            "discord": False,
            "database": True,
        }
    )

    with (
        patch.object(jobs, "application", application),
        patch("app.services.jobs.HealthService.check", return_value=health_result),
        patch("app.integrations.paratranz.ParaTranzClient.project_snapshot", side_effect=RuntimeError),
        patch("app.integrations.discord.DiscordClient.snapshot", side_effect=RuntimeError),
        patch.object(jobs, "Automation") as automation_cls,
    ):
        automation_cls.return_value._embed_if_changed.side_effect = RuntimeError("discord unavailable")
        result = jobs.health()

    assert result["status"] == "degraded"
    assert any(
        event_type == "automation.delivery_failed"
        and payload["operation"] == "health"
        for event_type, payload in events
    )

def test_report_generation_survives_discord_delivery_failure():
    events = []
    database = SimpleNamespace(
        recent_snapshots=lambda limit: [{
            "payload": {
                "project": {
                    "translation_percent": 12.0,
                    "review_percent": 3.0,
                    "translated": 12,
                    "strings_total": 100,
                }
            }
        }]
    )
    settings = SimpleNamespace(channel_reports="reports")
    application = SimpleNamespace(
        context=SimpleNamespace(settings=settings, database=database)
    )
    application.record = lambda event_type, payload: events.append((event_type, payload))

    with (
        patch.object(jobs, "application", application),
        patch.object(jobs.DiscordNotificationService, "embed", side_effect=RuntimeError("discord unavailable")),
    ):
        result = jobs.report("daily")

    assert result["period"] == "daily"
    assert ("report.generated", result) in events
    assert any(
        event_type == "automation.delivery_failed"
        and payload["operation"] == "report.daily"
        for event_type, payload in events
    )
