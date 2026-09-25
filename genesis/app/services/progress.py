from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MemberProgress:
    member_id: str
    completed: int
    review: int
    active: int


class ProgressService:
    def member(self, member_id: str, completed: int, review: int, active: int) -> MemberProgress:
        return MemberProgress(member_id, max(0, completed), max(0, review), max(0, active))
