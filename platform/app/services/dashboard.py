from __future__ import annotations

from app.services.analytics import AnalyticsService


class DashboardService:
    """Builds a secret-free public view from canonical platform snapshots."""

    def __init__(self):
        self.analytics = AnalyticsService()

    def public_contract(self, snapshot: dict) -> dict:
        project = snapshot.get("project", {})
        return {
            "schema": 1,
            "project": {
                "project_id": project.get("project_id"),
                "words_total": project.get("words_total", 0),
                "strings_total": project.get("strings_total", 0),
                "translated": project.get("translated", 0),
                "reviewed": project.get("reviewed", 0),
                "files": project.get("files", 0),
                "translation_percent": project.get("translation_percent", 0),
                "review_percent": project.get("review_percent", 0),
            },
            "health": snapshot.get("health", {}),
            "discord": {
                "guild_name": (snapshot.get("discord") or {}).get("guild_name"),
                "channels": len((snapshot.get("discord") or {}).get("channels", [])),
                "roles": len((snapshot.get("discord") or {}).get("roles", [])),
            },
        }
