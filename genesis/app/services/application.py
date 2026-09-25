from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.persistence.store import Store
from app.services.achievements import AchievementService
from app.services.alerts import AlertService
from app.services.glossary import GlossaryService
from app.services.health import HealthService
from app.services.missions import MissionService
from app.services.review import ReviewQueue
from app.services.tasks import TaskService
from app.services.translation import TranslationService
from app.services.progress import ProgressService
from app.services.scheduling import ReminderService
from app.services.events import EventService
from app.services.mission_engine import MissionEngineService
from app.services.sync import SyncService
from app.services.command_center import CommandCenterService


class GenesisApplication:
    """The only application boundary used by transports."""

    def __init__(self, store: Store):
        self.store = store
        self.translation = TranslationService()
        self.glossary = GlossaryService()
        self.events = EventService(store)
        self.tasks = TaskService(store, self.events)
        self.missions = MissionService()
        self.reviews = ReviewQueue(store)
        self.achievements = AchievementService()
        self.alerts = AlertService()
        self.health = HealthService()
        self.progress = ProgressService()
        self.reminders = ReminderService(store)
        self.sync = SyncService()
        from app.services.scheduling import MissionScheduler
        self.mission_scheduler = MissionScheduler(store)
        self.mission_engine = MissionEngineService(store, self.missions, self.tasks, self.events)
        self.command_center = CommandCenterService(self)

    def initialize(self) -> None:
        self.store.initialize()

    def audit(self, event_type: str, actor: str | None, payload: dict[str, Any]) -> None:
        self.store.record_event(
            event_type,
            actor,
            datetime.now(timezone.utc).isoformat(),
            payload,
        )
