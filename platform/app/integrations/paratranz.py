from __future__ import annotations

from datetime import datetime, timezone

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
        project_url = f"{self.base_url}/projects/{self.settings.paratranz_project_id}"
        files_url = f"{project_url}/files"

        # ParaTranz exposes aggregate translation counters on each file, not
        # as wordCount/stringCount/fileCount fields on the project metadata.
        with httpx.Client(headers=headers, timeout=30) as client:
            project_response = client.get(project_url)
            project_response.raise_for_status()
            project = project_response.json()

            files_response = client.get(files_url)
            files_response.raise_for_status()
            files = files_response.json()

        if not isinstance(project, dict):
            raise ValueError("ParaTranz returned a non-object project response")
        if not isinstance(files, list):
            raise ValueError("ParaTranz returned a non-list file response")

        required_metrics = ("total", "translated", "reviewed", "words")
        totals = {key: 0 for key in required_metrics}
        for index, item in enumerate(files):
            if not isinstance(item, dict):
                raise ValueError(f"ParaTranz file entry {index} is not an object")
            missing = [key for key in required_metrics if key not in item or item[key] is None]
            if missing:
                file_name = item.get("name", str(index))
                raise ValueError(
                    f"ParaTranz file {file_name!r} missing metrics: {', '.join(missing)}"
                )
            try:
                for key in required_metrics:
                    value = int(item[key])
                    if value < 0:
                        raise ValueError(f"negative {key}")
                    totals[key] += value
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"ParaTranz file {item.get('name', str(index))!r} has invalid metrics"
                ) from exc

        # Do not publish a plausible-looking zero snapshot if the API payload
        # is empty, incomplete, or inconsistent.
        if totals["total"] <= 0 or totals["words"] <= 0:
            raise ValueError("ParaTranz returned an empty project snapshot")
        if totals["translated"] > totals["total"] or totals["reviewed"] > totals["total"]:
            raise ValueError("ParaTranz project counters exceed total strings")

        # The documented Project schema defines members as a numeric count.
        raw_members = project.get("members")
        if raw_members is None:
            raise ValueError("ParaTranz project response missing member count")
        try:
            member_count = int(raw_members)
        except (TypeError, ValueError) as exc:
            raise ValueError("ParaTranz returned an invalid project member count") from exc
        if member_count < 0:
            raise ValueError("ParaTranz returned a negative project member count")

        return ProjectSnapshot(
            project_id=self.settings.paratranz_project_id,
            captured_at=datetime.now(timezone.utc),
            words_total=totals["words"],
            strings_total=totals["total"],
            translated=totals["translated"],
            reviewed=totals["reviewed"],
            files=len(files),
            members=member_count,
        )
