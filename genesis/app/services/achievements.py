from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.persistence.store import Store


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
    def __init__(self, store: Store | None = None):
        self.store = store

    def earned(self, completed_tasks: int, clean_reviews: int = 0, member_id: str | None = None) -> list[Achievement]:
        values = {"first_task": completed_tasks, "ten_tasks": completed_tasks, "clean_review": clean_reviews}
        earned = [a for a in ACHIEVEMENTS if values[a.key] >= a.threshold]
        if self.store and member_id:
            now = datetime.now(timezone.utc).isoformat()
            for achievement in earned:
                self.store.award_achievement(member_id, achievement.key, now)
        return earned

    def persisted(self, member_id: str) -> list[Achievement]:
        keys = {row["achievement_key"] for row in self.store.achievements(member_id)} if self.store else set()
        return [a for a in ACHIEVEMENTS if a.key in keys]
