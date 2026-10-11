from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.domain.models import TranslationCheck


class ReviewDecision:
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request_changes"


@dataclass(frozen=True)
class ReviewItem:
    id: int
    actor: str
    check: TranslationCheck
    created_at: str


class ReviewQueue:
    def __init__(self) -> None:
        self._items: list[ReviewItem] = []
        self._next_id = 1

    def submit(self, actor: str, check: TranslationCheck) -> ReviewItem:
        item = ReviewItem(
            id=self._next_id,
            actor=actor,
            check=check,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._next_id += 1
        self._items.append(item)
        return item

    def pending(self) -> list[ReviewItem]:
        return list(self._items)

    def decide(self, item_id: int, decision: str, reviewer: str) -> dict:
        if decision not in {
            ReviewDecision.APPROVE,
            ReviewDecision.REJECT,
            ReviewDecision.REQUEST_CHANGES,
        }:
            raise ValueError("invalid review decision")
        item = next((x for x in self._items if x.id == item_id), None)
        if item is None:
            raise KeyError(item_id)
        self._items.remove(item)
        return {"item_id": item_id, "decision": decision, "reviewer": reviewer}
