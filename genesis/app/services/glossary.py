from __future__ import annotations

from app.domain.models import GlossaryTerm


class GlossaryService:
    """Authoritative in-memory read model backed by durable ParaTranz snapshots."""

    def __init__(self, terms: list[GlossaryTerm] | None = None):
        self._terms = terms or []
        self._index = {term.source.casefold(): term for term in self._terms}

    def replace(self, terms: list[GlossaryTerm]) -> None:
        deduped: dict[str, GlossaryTerm] = {}
        for term in terms:
            source, target = term.source.strip(), term.target.strip()
            if source and target:
                deduped[source.casefold()] = GlossaryTerm(source, target, term.status)
        self._terms = list(deduped.values())
        self._index = {term.source.casefold(): term for term in self._terms}

    def all(self) -> list[GlossaryTerm]:
        return list(self._terms)

    def find(self, source: str) -> list[GlossaryTerm]:
        term = self._index.get(source.strip().casefold())
        return [] if term is None else [term]

    def suggestions(self, source_text: str) -> list[GlossaryTerm]:
        lowered = source_text.casefold()
        return [term for term in self._terms if term.source.casefold() in lowered]

    def validate(self) -> dict:
        sources = [t.source.casefold() for t in self._terms]
        duplicates = len(sources) - len(set(sources))
        invalid = sum(not t.source.strip() or not t.target.strip() for t in self._terms)
        return {"terms": len(self._terms), "duplicates": duplicates, "invalid": invalid, "healthy": duplicates == 0 and invalid == 0}
