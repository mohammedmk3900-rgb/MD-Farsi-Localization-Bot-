"""Central configuration for MD Farsi Localization Command Center V6."""
from __future__ import annotations
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Config:
    project_id: int = int(os.getenv("PARATRANZ_PROJECT_ID", "19621"))
    participants: int = int(os.getenv("PROJECT_PARTICIPANTS", "8"))
    paratranz_token: str = os.getenv("PARATRANZ_TOKEN", "").strip()
    stats_webhook: str = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    progress_webhook: str = os.getenv("DISCORD_PROGRESS_WEBHOOK_URL", "").strip()
    achievements_webhook: str = os.getenv("DISCORD_ACHIEVEMENTS_WEBHOOK_URL", "").strip()
    health_webhook: str = os.getenv("DISCORD_HEALTH_WEBHOOK_URL", "").strip()
    reports_webhook: str = os.getenv("DISCORD_REPORTS_WEBHOOK_URL", "").strip()
    history_limit: int = int(os.getenv("COMMAND_CENTER_HISTORY_LIMIT", "180"))
    sync_hours: int = int(os.getenv("COMMAND_CENTER_SYNC_HOURS", "6"))

    @property
    def project_url(self) -> str:
        return f"https://paratranz.cn/projects/{self.project_id}"

    @property
    def api_url(self) -> str:
        return f"https://paratranz.cn/api/projects/{self.project_id}/files"
