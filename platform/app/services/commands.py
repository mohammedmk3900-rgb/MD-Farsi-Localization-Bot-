from __future__ import annotations

from app.application import application
from app.services.glossary import GlossaryService
from app.services.reports import ReportService
from app.services.sync import sync_project
from app.services.tasks import TaskService
from app.services.translation_assistant import TranslationAssistant


class CommandService:
    """Command facade. Read commands use stored state; sync() is the explicit live fetch."""

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
        return {"page": page, "page_size": page_size, "items": GlossaryService(application.context.settings).page(page, page_size)}

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

    def tasks(self, status: str | None = None, owner: str | None = None) -> list[dict]:
        return TaskService(application.context.database).list(status=status, owner=owner)

    def task_summary(self) -> dict[str, int]:
        return TaskService(application.context.database).summary()

    def create_task(self, title: str, scope: str = "", priority: str = "normal") -> dict:
        return TaskService(application.context.database).create(title, scope=scope, priority=priority)

    def claim_task(self, task_id: int, owner: str) -> dict:
        return TaskService(application.context.database).claim(task_id, owner)

    def submit_task(self, task_id: int, owner: str) -> dict:
        return TaskService(application.context.database).submit(task_id, owner)

    def complete_task(self, task_id: int, reviewer: str) -> dict:
        return TaskService(application.context.database).complete(task_id, reviewer)

    def check_translation(self, source: str, translation: str, glossary: list[dict] | None = None) -> dict:
        if glossary is None:
            try:
                glossary = GlossaryService(application.context.settings).sync_all(max_entries=5000)
            except Exception:
                glossary = []
        return TranslationAssistant().check(source, translation, glossary)

    def command_center(self) -> dict:
        return {
            "status": self.health(),
            "project": self.stats(),
            "tasks": self.task_summary(),
            "human_approval_required": True,
            "auto_publish": False,
        }

    def help(self) -> list[str]:
        return [
            "/project status", "/project stats", "/project progress",
            "/project glossary", "/project history", "/project health",
            "/project achievements", "/project sync", "/project report",
            "/project center", "/project tasks", "/project task_create",
            "/project task_claim", "/project task_submit", "/project task_complete",
            "/project check",
        ]
