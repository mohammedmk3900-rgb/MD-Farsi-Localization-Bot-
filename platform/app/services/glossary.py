from __future__ import annotations

import json
from pathlib import Path

from app.integrations.paratranz_terms import ParaTranzTerms


class GlossaryService:
    def __init__(self, settings):
        self.client = ParaTranzTerms(settings.paratranz_project_id, settings.paratranz_token)

    def page(self, page: int = 1, page_size: int = 100) -> list[dict]:
        return self.client.list(page, page_size)

    def sync_all(self, max_entries: int = 5000, page_size: int = 100) -> list[dict]:
        terms: list[dict] = []
        page = 1
        while len(terms) < max_entries:
            batch = self.page(page, min(page_size, max_entries - len(terms)))
            if not batch:
                break
            terms.extend(batch)
            if len(batch) < page_size:
                break
            page += 1

        terms = terms[:max_entries]
        output = Path("data/glossary.json")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(terms, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return terms
