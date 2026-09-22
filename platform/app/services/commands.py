from __future__ import annotations

from app.application import application
from app.services.glossary import GlossaryService
from app.services.reports import ReportService
from app.services.sync import sync_project


class CommandService:
    """Read-only command facade; only sync() performs a live project fetch."""

    def _latest_project(self) -> dict:
        rows = application.context.database.recent_snapshots(50)
        for row in rows:
            project = row["payload"].get("project")
            if project:
                return project
        return {}

    def status(self) -> dict:
        return {"ok": True, "service": "md-news", "project_id": application.context.settings.paratranz_project_id}

    def health(self) -> dict:
        settings = application.context.settings
        return {
            "status": "ok",
            "database": settings.database_path,
            "paratranz_configured": bool(settings.paratranz_token),
            "discord_configured": bool(settings.discord_bot_token and settings.discord_guild_id),
            "history_entries": len(application.context.database.recent_snapshots(1)),
        }

    def stats(self) -> dict:
        project = self._latest_project()
        return {
            "words_total": project.get("words_total", 0),
            "strings_total": project.get("strings_total", 0),
            "translated": project.get("translated", 0),
            "reviewed": project.get("reviewed", 0),
            "files": project.get("files", 0),
            "translation_percent": project.get("translation_percent", 0),
            "review_percent": project.get("review_percent", 0),
            "synced": bool(project),
        }

    def progress(self) -> dict:
        stats = self.stats()
        return {k: stats[k] for k in ("translation_percent", "review_percent", "translated", "reviewed", "synced")}

    def glossary(self, page: int = 1, page_size: int = 20) -> dict:
        return {"page": page, "page_size": page_size,
                "items": GlossaryService(application.context.settings).page(page, page_size)}

    def history(self, limit: int = 10) -> list[dict]:
        return application.context.database.recent_snapshots(limit)

    def achievements(self) -> dict:
        project = self._latest_project()
        percent = project.get("translation_percent", 0)
        return {"milestones": [x for x in (1, 10, 25, 50, 75, 100) if percent >= x]}

    def sync(self) -> dict:
        return sync_project()

    def report(self, period: str = "daily") -> dict:
        project = self._latest_project()
        if not project:
            return {"period": period, "status": "no_snapshot", "project": None}
        return ReportService().build({"project": project}, period=period)

    def help(self) -> list[str]:
        return [
            "/project status", "/project stats", "/project progress",
            "/project glossary", "/project history", "/project health",
            "/project achievements", "/project sync", "/project report",
        ]
