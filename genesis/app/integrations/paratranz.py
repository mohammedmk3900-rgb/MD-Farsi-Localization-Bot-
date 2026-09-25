from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.integrations.contracts import ProjectStats


class ParaTranzError(RuntimeError):
    pass


@dataclass(frozen=True)
class ParaTranzConfig:
    project_id: int
    base_url: str = "https://paratranz.cn/api"

    @classmethod
    def from_env(cls) -> "ParaTranzConfig":
        raw = os.getenv("PARATRANZ_PROJECT_ID", "19621")
        return cls(project_id=int(raw), base_url=os.getenv("PARATRANZ_BASE_URL", "https://paratranz.cn/api").rstrip("/"))


class ParaTranzIntegration:
    """Read-only ParaTranz adapter.

    Authentication is optional for public project reads and is never persisted.
    Genesis deliberately exposes no automatic translation publication operation.
    """

    def __init__(self, config: ParaTranzConfig | None = None, token: str | None = None, timeout: float = 15.0):
        self.config = config or ParaTranzConfig.from_env()
        self.token = token if token is not None else os.getenv("PARATRANZ_TOKEN")
        self.timeout = timeout

    def _get(self, path: str) -> object:
        request = Request(f"{self.config.base_url}/{path.lstrip('/')}", method="GET")
        request.add_header("Accept", "application/json")
        if self.token:
            request.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            raise ParaTranzError(f"ParaTranz request failed: {exc}") from exc

    @staticmethod
    def _payload(data: object) -> dict:
        if isinstance(data, dict):
            return data.get("data", data)
        raise ParaTranzError("Unexpected ParaTranz response payload")

    def project(self) -> dict:
        return self._payload(self._get(f"projects/{self.config.project_id}"))

    def stats(self) -> ProjectStats:
        data = self.project()
        stats = data.get("stats", data.get("statistics", {}))
        return ProjectStats(
            project_id=self.config.project_id,
            words_total=int(stats.get("words", stats.get("wordsTotal", 0)) or 0),
            strings_total=int(stats.get("strings", stats.get("stringsTotal", 0)) or 0),
            translated=int(stats.get("translated", stats.get("translatedStrings", 0)) or 0),
            reviewed=int(stats.get("reviewed", stats.get("reviewedStrings", 0)) or 0),
            files=int(data.get("files", data.get("fileCount", 0)) if not isinstance(data.get("files"), list) else len(data["files"])),
            members=int(data.get("members", data.get("memberCount", 0)) if not isinstance(data.get("members"), list) else len(data["members"])),
        )

    def glossary(self) -> list[dict]:
        # ParaTranz Terms is the project's glossary source of truth.
        data = self._payload(self._get(f"projects/{self.config.project_id}/terms"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            terms = data.get("terms", data.get("items", []))
            return terms if isinstance(terms, list) else []
        return []
