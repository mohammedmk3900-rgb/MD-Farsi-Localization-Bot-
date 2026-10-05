from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.persistence.store import Store
from app.services.achievements import AchievementService
from app.services.alerts import AlertService
from app.services.command_center import CommandCenterService
from app.services.glossary import GlossaryService
from app.services.health import HealthService
from app.services.missions import MissionService
from app.services.progress import ProgressService
from app.services.review import ReviewQueue
from app.services.scheduling import ReminderService, Scheduler
from app.services.sync import SyncService
from app.services.tasks import TaskService
from app.services.translation import TranslationService


class GenesisApplication:
    """Single application boundary exposed to transports such as Discord."""

    def __init__(self, store: Store):
        self.store = store
        self.translation = TranslationService()
        self.glossary = GlossaryService()
        self.tasks = TaskService(store)
        self.missions = MissionService()
        self.reviews = ReviewQueue(store)
        self.achievements = AchievementService()
        self.alerts = AlertService(store)
        self.health = HealthService()
        self.progress = ProgressService()
        self.reminders = ReminderService()
        self.scheduler = Scheduler(store)
        self.sync = SyncService()
        self.command_center = CommandCenterService(self)

    def initialize(self) -> None:
        self.store.initialize()
        self.audit("genesis.initialized", None, {"schema": 3})

    def audit(self, event_type: str, actor: str | None, payload: dict[str, Any]) -> None:
        self.store.record_event(event_type, actor, datetime.now(timezone.utc).isoformat(), payload)
