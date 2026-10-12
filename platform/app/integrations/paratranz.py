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

        # ParaTranz's project endpoint provides project metadata, while the
        # per-file endpoint contains total/translated/reviewed/words counters.
        # Do not assume aggregate metrics exist on the project object itself.
        with httpx.Client(headers=headers, timeout=30) as client:
            response = client.get(project_url)
            response.raise_for_status()
            project = response.json()

            files_response = client.get(files_url)
            files_response.raise_for_status()
            files = files_response.json()

        if not isinstance(project, dict):
            raise ValueError("ParaTranz returned a non-object project response")
        if not isinstance(files, list):
            raise ValueError("ParaTranz returned a non-list file response")

        required_file_metrics = ("total", "translated", "reviewed", "words")
        totals = {key: 0 for key in required_file_metrics}
        for index, item in enumerate(files):
            if not isinstance(item, dict):
                raise ValueError(f"ParaTranz file entry {index} is not an object")
            missing = [
                key for key in required_file_metrics
                if key not in item or item[key] is None
            ]
            if missing:
                file_name = item.get("name", str(index))
                raise ValueError(
                    f"ParaTranz file {file_name!r} missing metrics: {', '.join(missing)}"
                )
            try:
                for key in required_file_metrics:
                    value = int(item[key])
                    if value < 0:
                        raise ValueError(f"negative {key}")
                    totals[key] += value
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"ParaTranz file {item.get('name', str(index))!r} has invalid metrics"
                ) from exc

        # The documented project payload exposes the member count as "members".
        # Support a list-shaped value too, in case an API variant returns members.
        raw_members = project.get("members")
        if isinstance(raw_members, list):
            member_count = len(raw_members)
        elif raw_members is not None:
            try:
                member_count = int(raw_members)
            except (TypeError, ValueError) as exc:
                raise ValueError("ParaTranz returned an invalid project member count") from exc
            if member_count < 0:
                raise ValueError("ParaTranz returned a negative project member count")
        else:
            # Some project responses omit the summary count; use the members
            # endpoint rather than fabricating a zero.
            with httpx.Client(headers=headers, timeout=30) as client:
                members_response = client.get(f"{project_url}/members")
                members_response.raise_for_status()
                members = members_response.json()
            if not isinstance(members, list):
                raise ValueError("ParaTranz returned a non-list member response")
            member_count = len(members)

        if totals["total"] <= 0 or totals["words"] <= 0:
            raise ValueError("ParaTranz returned an empty project snapshot")
        if totals["translated"] > totals["total"] or totals["reviewed"] > totals["total"]:
            raise ValueError("ParaTranz project counters exceed total strings")

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
