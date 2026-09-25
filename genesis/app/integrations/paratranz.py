from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.integrations.contracts import ProjectStats


class ParaTranzClient(Protocol):
    def get_project(self, project_id: int) -> dict[str, Any]: ...
    def get_terms(self, project_id: int) -> list[dict[str, Any]]: ...


@dataclass
class ParaTranzIntegration:
    """Adapter boundary; HTTP implementation is deliberately kept outside domain code."""

    client: ParaTranzClient
    project_id: int

    def stats(self) -> ProjectStats:
        raw = self.client.get_project(self.project_id)
        return ProjectStats(
            project_id=self.project_id,
            words_total=int(raw.get("words_total", 0)),
            strings_total=int(raw.get("strings_total", 0)),
            translated=int(raw.get("translated", 0)),
            reviewed=int(raw.get("reviewed", 0)),
            files=int(raw.get("files", 0)),
            members=int(raw.get("members", 0)),
        )

    def glossary(self) -> list[dict[str, Any]]:
        return self.client.get_terms(self.project_id)
