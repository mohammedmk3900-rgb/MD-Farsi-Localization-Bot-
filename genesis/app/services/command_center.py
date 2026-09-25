from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app.integrations.paratranz import ParaTranzIntegration


class CommandCenterService:
    """Read-model facade for Discord and future transports."""

    def __init__(self, application):
        self.application = application

    def status(self) -> dict[str, Any]:
        return {
            "tasks": self.application.tasks.summary(),
            "health": asdict(self.application.health.evaluate()),
            "glossary_terms": len(self.application.glossary.all()),
        }

    def project_sync(self) -> dict[str, Any]:
        return self.application.sync.project(self.application, ParaTranzIntegration())
