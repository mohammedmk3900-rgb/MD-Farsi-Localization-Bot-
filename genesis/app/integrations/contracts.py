from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ProjectStats:
    project_id: int
    words_total: int
    strings_total: int
    translated: int
    reviewed: int
    files: int
    members: int


class TranslationSource(Protocol):
    def project_stats(self) -> ProjectStats: ...

    def glossary_terms(self) -> list[dict]: ...
