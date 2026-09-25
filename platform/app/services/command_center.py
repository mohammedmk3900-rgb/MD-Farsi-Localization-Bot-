from __future__ import annotations

from datetime import datetime, timezone

from app.config import Settings
from app.domain.models import CommandCenterSnapshot, HealthStatus, ProjectSnapshot
from app.integrations.discord import DiscordClient
from app.integrations.paratranz import ParaTranzClient
from app.persistence.database import Database
from app.services.analytics import AnalyticsService


class CommandCenter:
    def __init__(self, settings: Settings, database: Database):
        self.settings = settings
        self.database = database
        self.analytics = AnalyticsService()

    def collect(self) -> CommandCenterSnapshot:
        captured = datetime.now(timezone.utc)
        project_error: Exception | None = None
        try:
            project = ParaTranzClient(self.settings).project_snapshot()
        except Exception as exc:
            project_error = exc
            previous = self.database.recent_snapshots(1)
            previous_project = previous[0]["payload"].get("project") if previous else None
            if not previous_project:
                raise
            # Persisted project snapshots include computed fields, while the
            # domain model forbids unknown fields during fallback validation.
            allowed = set(ProjectSnapshot.model_fields)
            project = ProjectSnapshot.model_validate(
                {key: value for key, value in previous_project.items() if key in allowed}
            )

        discord = None
        discord_configured = bool(
            self.settings.discord_bot_token and self.settings.discord_guild_id
        )
        discord_ok = False
        if discord_configured:
            try:
                discord = DiscordClient(self.settings).snapshot()
                discord_ok = True
            except Exception:
                # ParaTranz is the project source of truth. A Discord outage must
                # degrade the snapshot rather than block project synchronization.
                discord = None

        health = HealthStatus(
            status="healthy" if (project_error is None and (not discord_configured or discord_ok)) else "degraded",
            checked_at=captured,
            paratranz=project_error is None,
            discord=discord_ok if discord_configured else False,
            database=True,
        )

        snapshot = CommandCenterSnapshot(
            captured_at=captured,
            project=project,
            discord=discord,
            health=health,
        )
        payload = snapshot.model_dump(mode="json")
        if project_error is not None:
            payload["health"]["status"] = "degraded"
        previous = self.database.recent_snapshots(1)
        previous_project = previous[0]["payload"].get("project") if previous else None

        self.database.save_snapshot(
            captured.isoformat(),
            snapshot.schema_version,
            payload,
        )
        self.database.append_event(
            "command_center.snapshot",
            captured.isoformat(),
            payload,
        )
        self.database.append_event(
            "project.delta",
            captured.isoformat(),
            self.analytics.delta(
                project.model_dump(mode="json"),
                previous_project,
            ),
        )
        return snapshot
