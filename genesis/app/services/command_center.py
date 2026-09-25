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

    def due_missions(self, now_iso: str | None = None) -> list:
        now_iso = now_iso or datetime.now(timezone.utc).isoformat()
        return self.application.mission_scheduler.due(now_iso)
