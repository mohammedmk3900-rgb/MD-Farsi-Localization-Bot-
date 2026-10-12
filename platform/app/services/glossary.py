from __future__ import annotations

import json
from pathlib import Path

from app.integrations.paratranz_terms import ParaTranzTerms


class GlossaryService:
    def __init__(self, settings):
        self.settings = settings
        self.client = ParaTranzTerms(
            settings.paratranz_project_id,
            settings.paratranz_token,
            base_url=getattr(settings, "paratranz_base_url", ParaTranzTerms.BASE),
            timeout=getattr(settings, "paratranz_timeout_seconds", 20.0),
            max_retries=getattr(settings, "paratranz_max_retries", 3),
        )

    def page(self, page: int = 1, page_size: int = 100) -> list[dict]:
        return self.client.list(page, page_size)

    def sync_all(self, max_entries: int = 5000, page_size: int = 100) -> list[dict]:
        if max_entries < 1:
            raise ValueError("max_entries must be >= 1")
        if not 1 <= page_size <= 1000:
            raise ValueError("page_size must be between 1 and 1000")

        terms: list[dict] = []
        seen: set[str] = set()
        previous_signature: str | None = None
        # A hard page cap protects the sync job if the upstream endpoint ignores
        # page parameters or returns malformed pagination metadata.
        max_pages = min(100, (max_entries + page_size - 1) // page_size + 1)

        for page in range(1, max_pages + 1):
            batch = self.page(page, min(page_size, max_entries - len(terms)))
            if not batch:
                break
            signature = json.dumps(batch, sort_keys=True, ensure_ascii=False, default=str)
            if signature == previous_signature:
                break
            previous_signature = signature

            for index, term in enumerate(batch):
                identity = term.get("id")
                key = f"id:{identity}" if identity is not None else f"json:{json.dumps(term, sort_keys=True, ensure_ascii=False, default=str)}"
                if key not in seen:
                    seen.add(key)
                    terms.append(term)
                if len(terms) >= max_entries:
                    break
            if len(terms) >= max_entries or len(batch) < min(page_size, max_entries - len(terms)):
                break

        terms = terms[:max_entries]
        # Never replace a known-good glossary with a suspicious empty result.
        output = Path(self.settings.database_path).parent / "glossary.json"
        if not terms and output.exists():
            try:
                previous = json.loads(output.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                previous = None
            if isinstance(previous, list) and previous:
                raise ValueError("Refusing to replace a populated glossary with an empty response")

        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(terms, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(output)
        return terms
