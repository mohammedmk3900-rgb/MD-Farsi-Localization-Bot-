"""Deterministic progress and milestone calculations."""
from __future__ import annotations
from .versioning import compare_month
from ..models import ProgressDelta, ProjectStats

MILESTONES = (1, 10, 25, 50, 75, 100)

def delta(current: ProjectStats, previous: dict) -> ProgressDelta:
    return ProgressDelta(
        translated=current.translated - int(previous.get("translated", current.translated)),
        reviewed=current.reviewed - int(previous.get("reviewed", current.reviewed)),
        translation_percent=round(current.translation_percent - float(previous.get("translation_percent", current.translation_percent)), 2),
        review_percent=round(current.review_percent - float(previous.get("review_percent", current.review_percent)), 2),
    )

def crossed(previous_percent: float, current_percent: float) -> list[int]:
    return [threshold for threshold in MILESTONES if previous_percent < threshold <= current_percent]
