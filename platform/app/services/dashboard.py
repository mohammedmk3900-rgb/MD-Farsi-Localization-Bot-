from __future__ import annotations


class DashboardService:
    """Build a stable, secret-free public view from a canonical snapshot."""

    def public_contract(self, snapshot: dict) -> dict:
        project = snapshot.get("project", {})
        discord = snapshot.get("discord") or {}
        return {
            "schema": 1,
            "captured_at": snapshot.get("captured_at"),
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
                "guild_name": discord.get("guild_name"),
                "channels": discord.get("channels", 0) if isinstance(discord.get("channels"), int) else len(discord.get("channels", [])),
                "roles": discord.get("roles", 0) if isinstance(discord.get("roles"), int) else len(discord.get("roles", [])),
            },
        }
