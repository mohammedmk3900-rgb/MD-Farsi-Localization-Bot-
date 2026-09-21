"""Typed domain models for Command Center state."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any

@dataclass(frozen=True)
class ProjectStats:
    files: int
    strings: int
    translated: int
    reviewed: int
    words: int

    @property
    def translation_percent(self) -> float:
        return round(self.translated / self.strings * 100, 2) if self.strings else 0.0

    @property
    def review_percent(self) -> float:
        return round(self.reviewed / self.strings * 100, 2) if self.strings else 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass(frozen=True)
class ProgressDelta:
    translated: int
    reviewed: int
    translation_percent: float
    review_percent: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass(frozen=True)
class Snapshot:
    timestamp: str
    epoch: int
    stats: ProjectStats
    delta: ProgressDelta
    milestones_crossed: list[int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "epoch": self.epoch,
            **self.stats.to_dict(),
            "translation_percent": self.stats.translation_percent,
            "review_percent": self.stats.review_percent,
            "delta_translated": self.delta.translated,
            "delta_reviewed": self.delta.reviewed,
            "delta_translation_percent": self.delta.translation_percent,
            "delta_review_percent": self.delta.review_percent,
            "milestones_crossed": self.milestones_crossed,
        }
