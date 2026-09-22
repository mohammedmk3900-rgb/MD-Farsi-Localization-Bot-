from __future__ import annotations

from datetime import datetime, timezone

from app.config import Settings
from app.domain.models import CommandCenterSnapshot, HealthStatus
from app.integrations.discord import DiscordClient
from app.integrations.paratranz import ParaTranzClient
from app.persistence.database import Database


class CommandCenter:
    def __init__(self, settings: Settings, database: Database):
        self.settings = settings
        self.database = database

    def collect(self) -> CommandCenterSnapshot:
        captured = datetime.now(timezone.utc)
        project = ParaTranzClient(self.settings).project_snapshot()

        discord = None
        discord_ok = False
        if self.settings.discord_bot_token and self.settings.discord_guild_id:
            discord = DiscordClient(self.settings).snapshot()
            discord_ok = True

        health = HealthStatus(
            status="healthy" if discord_ok else "degraded",
            checked_at=captured,
            paratranz=True,
            discord=discord_ok,
            database=True,
        )

        snapshot = CommandCenterSnapshot(
            captured_at=captured,
            project=project,
            discord=discord,
            health=health,
        )
        self.database.append_event(
            "command_center.snapshot",
            captured.isoformat(),
            snapshot.model_dump(mode="json"),
        )
        return snapshot
