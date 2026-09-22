from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.config import Settings
from app.persistence.database import Database


@dataclass(frozen=True)
class ApplicationContext:
    settings: Settings
    database: Database


class PlatformApplication:
    """Single application boundary for Discord, ParaTranz and project automation."""

    def __init__(self, context: ApplicationContext):
        self.context = context

    def now(self) -> datetime:
        return datetime.now(timezone.utc)

    def record(self, event_type: str, payload: dict) -> None:
        self.context.database.append_event(
            event_type,
            self.now().isoformat(),
            payload,
        )
