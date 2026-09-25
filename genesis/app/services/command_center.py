from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.integrations.paratranz import ParaTranzIntegration


class CommandCenterService:
    """Transport-neutral operational facade."""

    def __init__(self, application):
        self.application = application

    def status(self) -> dict[str, Any]:
        health = self.application.health.evaluate({
            "store": "ok",
            "translation": "ok",
            "glossary": "ok",
        })
        return {
            "tasks": self.application.tasks.summary(),
            "health": {"status": health.status, "checks": health.checks},
            "glossary_terms": len(self.application.glossary.all()),
            "review_pending": len(self.application.reviews.pending()),
        }

    def tasks(self, status=None) -> list:
        return self.application.tasks.list(status)

    def review_queue(self) -> list:
        return self.application.reviews.pending()

    def project_sync(self) -> dict[str, Any]:
        return self.application.sync.project(self.application, ParaTranzIntegration())

    def due_reminders(self, now_iso: str | None = None) -> list:
        now_iso = now_iso or datetime.now(timezone.utc).isoformat()
        return self.application.reminders.due(now_iso)

    def missions(self, status: str | None = None) -> list:
        return self.application.mission_engine.list(status)

    def generate_missions(self, scopes: list[str], limit: int = 5) -> list:
        return self.application.mission_engine.generate(scopes, limit)

    def activate_mission(self, mission_id: int):
        return self.application.mission_engine.activate(mission_id)

    def complete_mission(self, mission_id: int, actor: str):
        return self.application.mission_engine.complete(mission_id, actor)

    def cancel_mission(self, mission_id: int, actor: str):
        return self.application.mission_engine.cancel(mission_id, actor)

    def events(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.application.events.recent(limit)

    def notifications(self, recipient: str) -> list:
        return self.application.events.pending_notifications(recipient)

    def due_missions(self, now_iso: str | None = None) -> list:
        now_iso = now_iso or datetime.now(timezone.utc).isoformat()
        return self.application.mission_scheduler.due(now_iso)
