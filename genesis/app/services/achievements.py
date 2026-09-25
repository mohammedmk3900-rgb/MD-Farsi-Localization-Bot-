from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Achievement:
    key: str
    title: str
    description: str
    threshold: int


ACHIEVEMENTS = (
    Achievement("first_task", "شروع عملیات", "اولین مأموریت را تکمیل کن.", 1),
    Achievement("ten_tasks", "ده‌گانه", "ده مأموریت را تکمیل کن.", 10),
    Achievement("clean_review", "ترجمه پاک", "یک ترجمه را بدون خطای فنی تحویل بده.", 1),
)


class AchievementService:
    def earned(self, completed_tasks: int, clean_reviews: int = 0) -> list[Achievement]:
        values = {"first_task": completed_tasks, "ten_tasks": completed_tasks, "clean_review": clean_reviews}
        return [a for a in ACHIEVEMENTS if values[a.key] >= a.threshold]
