from __future__ import annotations

from typing import Any


class AnalyticsService:
    """Pure project analytics; no Discord/network side effects."""

    def delta(self, current: dict[str, Any], previous: dict[str, Any] | None) -> dict[str, float]:
        previous = previous or {}
        keys = ("translated", "reviewed", "words_total", "strings_total", "files")
        return {f"delta_{k}": float(current.get(k, 0) or 0) - float(previous.get(k, 0) or 0) for k in keys}

    def milestones(self, previous_percent: float, current_percent: float) -> list[int]:
        levels = (1, 10, 25, 50, 75, 100)
        return [level for level in levels if previous_percent < level <= current_percent]
