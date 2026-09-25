from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class TaskStatus(StrEnum):
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    CANCELLED = "cancelled"


class Priority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass(frozen=True)
class GlossaryTerm:
    source: str
    target: str
    status: str = "🟢 ثابت"


@dataclass
class TranslationCheck:
    source: str
    translation: str
    findings: list[dict] = field(default_factory=list)

    @property
    def approved_for_review(self) -> bool:
        return not self.findings

    @property
    def publish_allowed(self) -> bool:
        return False


@dataclass
class Task:
    id: int
    title: str
    scope: str = ""
    owner: str | None = None
    reviewer: str | None = None
    priority: Priority = Priority.NORMAL
    status: TaskStatus = TaskStatus.AVAILABLE
    due_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
