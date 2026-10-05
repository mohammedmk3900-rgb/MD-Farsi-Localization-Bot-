from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class TaskStatus(StrEnum):
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    CANCELLED = "cancelled"


TASK_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.AVAILABLE: frozenset({TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED}),
    TaskStatus.IN_PROGRESS: frozenset({TaskStatus.REVIEW, TaskStatus.CANCELLED}),
    TaskStatus.REVIEW: frozenset({TaskStatus.DONE, TaskStatus.IN_PROGRESS}),
    TaskStatus.DONE: frozenset(),
    TaskStatus.CANCELLED: frozenset(),
}


def validate_task_transition(current: TaskStatus, target: TaskStatus) -> None:
    if target not in TASK_TRANSITIONS[current]:
        raise ValueError(f"invalid task transition: {current.value} -> {target.value}")


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
