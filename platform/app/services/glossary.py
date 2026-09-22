from __future__ import annotations

from app.integrations.paratranz_terms import ParaTranzTerms


class GlossaryService:
    def __init__(self, settings):
        self.client = ParaTranzTerms(settings.paratranz_project_id, settings.paratranz_token)

    def page(self, page: int = 1, page_size: int = 100) -> list[dict]:
        return self.client.list(page, page_size)
