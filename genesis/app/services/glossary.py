from __future__ import annotations

from app.domain.models import GlossaryTerm


class GlossaryService:
    def __init__(self, terms: list[GlossaryTerm] | None = None):
        self._terms = terms or []

    def replace(self, terms: list[GlossaryTerm]) -> None:
        self._terms = list(terms)

    def all(self) -> list[GlossaryTerm]:
        return list(self._terms)

    def find(self, source: str) -> list[GlossaryTerm]:
        needle = source.casefold()
        return [term for term in self._terms if term.source.casefold() == needle]

    def suggestions(self, source_text: str) -> list[GlossaryTerm]:
        lowered = source_text.casefold()
        return [term for term in self._terms if term.source.casefold() in lowered]
