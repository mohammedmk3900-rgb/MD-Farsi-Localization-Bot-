from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.persistence.store import Store


@dataclass(frozen=True)
class MemberProgress:
    member_id: str
    completed: int
    review: int
    active: int

    @property
    def total(self) -> int:
        return self.completed + self.review + self.active


class ProgressService:
    def __init__(self, store: Store | None = None):
        self.store = store

    def member(self, member_id: str, completed: int | None = None, review: int | None = None,
               active: int | None = None) -> MemberProgress:
        if self.store:
            row = self.store.member_progress(member_id)
            if row and completed is None and review is None and active is None:
                return MemberProgress(member_id, row["completed"], row["review"], row["active"])
        progress = MemberProgress(member_id, max(0, completed or 0), max(0, review or 0), max(0, active or 0))
        if self.store:
            self.store.upsert_member_progress(member_id, progress.completed, progress.review, progress.active,
                                               datetime.now(timezone.utc).isoformat())
        return progress

    def refresh_from_tasks(self, member_id: str) -> MemberProgress:
        if not self.store:
            return self.member(member_id)
        tasks = self.store.tasks()
        owned = [t for t in tasks if t["owner"] == member_id]
        return self.member(
            member_id,
            completed=sum(t["status"] == "done" for t in owned),
            review=sum(t["status"] == "review" for t in owned),
            active=sum(t["status"] == "in_progress" for t in owned),
        )
