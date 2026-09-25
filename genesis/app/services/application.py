from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.persistence.store import Store
from app.services.tasks import TaskService
from app.services.translation import TranslationService


class GenesisApplication:
    """Single application boundary. Transport layers call this facade only."""

    def __init__(self, store: Store):
        self.store = store
        self.translation = TranslationService()
        self.tasks = TaskService()

    def initialize(self) -> None:
        self.store.initialize()

    def audit(self, event_type: str, actor: str | None, payload: dict[str, Any]) -> None:
        self.store.record_event(
            event_type=event_type,
            actor=actor,
            created_at=datetime.now(timezone.utc).isoformat(),
            payload=payload,
        )
