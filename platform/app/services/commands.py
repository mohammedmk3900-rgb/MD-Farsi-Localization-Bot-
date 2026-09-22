from __future__ import annotations

from app.application import application
from app.services.reports import ReportService
from app.services.sync import sync_project


class CommandService:
    """Command layer for MD news. Commands contain no business rules."""

    def status(self) -> dict:
        return {
            "ok": True,
            "service": "md-news",
            "project_id": application.context.settings.paratranz_project_id,
        }

    def health(self) -> dict:
        return {
            "status": "ok",
            "database": application.context.settings.database_path,
        }

    def stats(self) -> dict:
        snapshot = sync_project()
        project = snapshot.get("project", snapshot)
        return {
            "words_total": project.get("words_total", 0),
            "strings_total": project.get("strings_total", 0),
            "translated": project.get("translated", 0),
            "reviewed": project.get("reviewed", 0),
            "files": project.get("files", 0),
            "translation_percent": project.get("translation_percent", 0),
            "review_percent": project.get("review_percent", 0),
        }

    def progress(self) -> dict:
        stats = self.stats()
        return {
            "translation_percent": stats["translation_percent"],
            "review_percent": stats["review_percent"],
            "translated": stats["translated"],
            "reviewed": stats["reviewed"],
        }

    def history(self, limit: int = 10) -> list[dict]:
        return application.context.database.recent_snapshots(limit)

    def achievements(self) -> dict:
        rows = self.history(1)
        if not rows:
            return {"milestones": []}
        percent = rows[0]["payload"]["project"].get("translation_percent", 0)
        levels = (1, 10, 25, 50, 75, 100)
        return {"milestones": [level for level in levels if percent >= level]}

    def report(self, period: str = "daily") -> dict:
        rows = self.history(1)
        if not rows:
            return {"period": period, "available": False}
        return ReportService().build(rows[0]["payload"], period=period)

    def help(self) -> list[str]:
        return [
            "/project stats",
            "/project progress",
            "/project glossary",
            "/project history",
            "/project health",
            "/project achievements",
            "/project sync",
            "/project report",
        ]
