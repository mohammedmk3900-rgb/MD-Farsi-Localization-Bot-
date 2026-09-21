from __future__ import annotations

from app.application import application


class CommandService:
    """Command layer for MD news. Commands call services; they never contain business rules."""

    def status(self) -> dict:
        return {"ok": True, "service": "md-news", "project_id": application.context.settings.paratranz_project_id}

    def health(self) -> dict:
        return {"status": "ok", "database": application.context.settings.database_path}

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
