from __future__ import annotations

from app.domain.permissions import allowed
from app.services.application import GenesisApplication
from app.services.reports import ReportService


class CommandCenter:
    """Single orchestration surface for Discord-facing operations."""

    def __init__(self, application: GenesisApplication):
        self.app = application
        self.reports = ReportService()

    def health(self, role: str) -> dict:
        self._require(role, "health.read")
        report = self.app.health.evaluate({"database": "ok"})
        return {"status": report.status, "checks": report.checks}

    def check_translation(self, role: str, source: str, translation: str) -> dict:
        self._require(role, "translation.check")
        result = self.app.translation.check(
            source,
            translation,
            self.app.glossary.suggestions(source),
        )
        return {
            "approved_for_review": result.approved_for_review,
            "publish_allowed": result.publish_allowed,
            "findings": result.findings,
        }

    def sync(self, role: str, integration) -> dict:
        self._require(role, "sync.run")
        return self.app.sync.project(self.app, integration)

    def pending_reviews(self, role: str) -> list:
        self._require(role, "tasks.review")
        return self.app.reviews.pending()

    def achievements(self, role: str, completed_tasks: int, clean_reviews: int = 0) -> list[dict]:
        self._require(role, "project.read")
        return [a.__dict__ for a in self.app.achievements.earned(completed_tasks, clean_reviews)]

    def _require(self, role: str, permission: str) -> None:
        if not allowed(role, permission):
            raise PermissionError(f"permission denied: {permission}")
