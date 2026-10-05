from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json

from app.domain.models import TranslationCheck
from app.persistence.store import Store


class ReviewDecision:
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request_changes"


class ReviewStatus:
    OPEN = "open"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"


@dataclass(frozen=True)
class ReviewItem:
    id: int
    actor: str
    check: TranslationCheck
    created_at: str
    status: str = ReviewStatus.OPEN


class ReviewQueue:
    """Durable human-in-the-loop review queue; no decision is automated."""

    def __init__(self, store: Store):
        self.store = store

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def submit(self, actor: str, check: TranslationCheck, translation_key: str | None = None) -> ReviewItem:
        key = translation_key or check.source
        created_at = self._now()
        review_id = self.store.create_review(
            translation_key=key, actor=actor, status=ReviewStatus.OPEN,
            created_at=created_at, source=check.source, translation=check.translation,
            findings=check.findings,
        )
        return ReviewItem(review_id, actor, check, created_at, ReviewStatus.OPEN)

    def pending(self) -> list[ReviewItem]:
        rows = self.store.reviews()
        return [
            ReviewItem(r["id"], r["actor"],
                       TranslationCheck(r.get("source", r["translation_key"]), r.get("translation", ""),
                                        json.loads(r.get("findings", "[]"))),
                       r["created_at"], r["status"])
            for r in rows if r["status"] in {ReviewStatus.OPEN, ReviewStatus.IN_REVIEW}
        ]

    def claim(self, item_id: int, reviewer: str) -> ReviewItem:
        row = next((r for r in self.store.reviews() if r["id"] == item_id), None)
        if row is None:
            raise KeyError(item_id)
        if row["status"] != ReviewStatus.OPEN:
            raise ValueError("review is not open")
        self.store.decide_review(
            item_id, reviewer=reviewer, decision=None, reason=None,
            status=ReviewStatus.IN_REVIEW, updated_at=self._now(), expected_status=ReviewStatus.OPEN
        )
        return ReviewItem(item_id, row["actor"],
                          TranslationCheck(row.get("source", row["translation_key"]), row.get("translation", ""),
                                           json.loads(row.get("findings", "[]"))),
                          row["created_at"], ReviewStatus.IN_REVIEW)

    def decide(self, item_id: int, decision: str, reviewer: str, reason: str | None = None) -> dict:
        if decision not in {ReviewDecision.APPROVE, ReviewDecision.REJECT, ReviewDecision.REQUEST_CHANGES}:
            raise ValueError("invalid review decision")
        status = {
            ReviewDecision.APPROVE: ReviewStatus.APPROVED,
            ReviewDecision.REJECT: ReviewStatus.REJECTED,
            ReviewDecision.REQUEST_CHANGES: ReviewStatus.CHANGES_REQUESTED,
        }[decision]
        self.store.decide_review(item_id, reviewer=reviewer, decision=decision, reason=reason,
                                 status=status, updated_at=self._now(), expected_status=ReviewStatus.IN_REVIEW)
        return {"item_id": item_id, "decision": decision, "reviewer": reviewer, "status": status}
