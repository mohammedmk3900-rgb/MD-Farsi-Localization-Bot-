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

        token = self.settings.paratranz_token.strip()
        authorization = token if token.lower().startswith("bearer ") else f"Bearer {token}"
        headers = {"Authorization": authorization}
        url = f"{self.base_url}/projects/{self.settings.paratranz_project_id}"
        with httpx.Client(headers=headers, timeout=30) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()

        # Reject malformed/empty API responses rather than overwriting a
        # previously valid snapshot with a fabricated all-zero report.
        if not isinstance(data, dict):
            raise ValueError("ParaTranz returned a non-object project response")
        required = ("wordCount", "stringCount", "translated", "reviewed", "fileCount", "memberCount")
        missing = [key for key in required if key not in data or data[key] is None]
        if missing:
            raise ValueError(f"ParaTranz response missing project metrics: {', '.join(missing)}")
        if int(data["stringCount"]) <= 0 or int(data["wordCount"]) <= 0:
            raise ValueError("ParaTranz returned an empty project snapshot")
        if int(data["translated"]) > int(data["stringCount"]) or int(data["reviewed"]) > int(data["stringCount"]):
            raise ValueError("ParaTranz project counters exceed total strings")

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
