from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable


@dataclass(frozen=True)
class ScheduledJob:
    name: str
    interval_minutes: int
    handler: Callable[[], object]


class Scheduler:
    """Application scheduler contract. GitHub Actions is not the business scheduler."""

    def __init__(self):
        self.jobs: list[ScheduledJob] = []

    def register(self, name: str, interval_minutes: int, handler: Callable[[], object]) -> None:
        if interval_minutes < 1:
            raise ValueError("interval_minutes must be positive")
        self.jobs.append(ScheduledJob(name, interval_minutes, handler))

    def manifest(self) -> dict:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "jobs": [
                {"name": j.name, "interval_minutes": j.interval_minutes}
                for j in self.jobs
            ],
        }
