from __future__ import annotations

from app.integrations.paratranz import ParaTranzAPI


class ParaTranzTerms:
    """Paginated read-only access to the project's ParaTranz glossary."""

    BASE = ParaTranzAPI.DEFAULT_BASE_URL

    def __init__(self, project_id: int, token: str, *, base_url: str = BASE,
                 timeout: float = 20.0, max_retries: int = 3):
        self.project_id = int(project_id)
        self.api = ParaTranzAPI(
            token,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )

    def list(self, page: int = 1, page_size: int = 100) -> list[dict]:
        items, _ = self.api.list_page(
            f"projects/{self.project_id}/terms",
            page=page,
            page_size=page_size,
            collection_keys=("terms",),
        )
        return items

    def list_all(self, page_size: int = 100, max_pages: int = 100) -> list[dict]:
        return self.api.list_all(
            f"projects/{self.project_id}/terms",
            page_size=page_size,
            max_pages=max_pages,
            collection_keys=("terms",),
        )
