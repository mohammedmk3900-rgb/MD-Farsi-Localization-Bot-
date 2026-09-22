from __future__ import annotations


class SecurityPolicy:
    """Central safety policy for automated project operations."""

    REVIEW_ACTIONS = frozenset({"approve", "reject", "finalize_review"})

    @classmethod
    def can_automate(cls, action: str) -> bool:
        return action not in cls.REVIEW_ACTIONS

    @classmethod
    def public_payload(cls, payload: dict) -> dict:
        blocked = {"token", "authorization", "webhook", "webhook_url", "member_id", "user_id"}
        return {k: v for k, v in payload.items() if k.lower() not in blocked}
