from __future__ import annotations

import httpx


class ParaTranzTerms:
    BASE = "https://paratranz.cn/api"

    def __init__(self, project_id: int, token: str):
        self.project_id = project_id
        self.token = token

    def list(self, page: int = 1, page_size: int = 100) -> list[dict]:
        if not self.token:
            raise ValueError("PARATRANZ_TOKEN is required")
        with httpx.Client(timeout=30) as client:
            response = client.get(
                f"{self.BASE}/projects/{self.project_id}/terms",
                params={"page": page, "pageSize": page_size},
                headers={"Authorization": f"Bearer {self.token}"},
            )
            response.raise_for_status()
            data = response.json()
        if isinstance(data, list):
            return data
        return data.get("data", data.get("terms", [])) if isinstance(data, dict) else []
