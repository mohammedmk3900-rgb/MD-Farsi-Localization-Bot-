from __future__ import annotations

import httpx

from app.config import Settings
from app.domain.models import ProjectSnapshot


class ParaTranzClient:
    base_url = "https://paratranz.cn/api"

    def __init__(self, settings: Settings):
        self.settings = settings

    def project_snapshot(self) -> ProjectSnapshot:
        if not self.settings.paratranz_token:
            raise RuntimeError("PARATRANZ_TOKEN is not configured")

        headers = {"Authorization": self.settings.paratranz_token}
        url = f"{self.base_url}/projects/{self.settings.paratranz_project_id}"
        with httpx.Client(headers=headers, timeout=30) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()

        return ProjectSnapshot(
            project_id=self.settings.paratranz_project_id,
            captured_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            words_total=int(data.get("wordCount", 0)),
            strings_total=int(data.get("stringCount", 0)),
            translated=int(data.get("translated", 0)),
            reviewed=int(data.get("reviewed", 0)),
            files=int(data.get("fileCount", 0)),
            members=int(data.get("memberCount", 0)),
        )
