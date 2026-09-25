from __future__ import annotations

from typing import TYPE_CHECKING

from app.domain.models import GlossaryTerm
from app.integrations.paratranz import ParaTranzIntegration

if TYPE_CHECKING:
    from app.services.application import GenesisApplication


class SyncService:
    def project(self, app: GenesisApplication, integration: ParaTranzIntegration) -> dict:
        stats = integration.stats()
        raw_terms = integration.glossary()
        terms = [
            GlossaryTerm(
                source=str(item["source"]),
                target=str(item["target"]),
                status=str(item.get("status", "🟢 ثابت")),
            )
            for item in raw_terms
            if item.get("source") and item.get("target")
        ]
        app.glossary.replace(terms)
        app.audit("paratranz.sync", None, {
            "project_id": stats.project_id,
            "translated": stats.translated,
            "reviewed": stats.reviewed,
            "files": stats.files,
            "members": stats.members,
            "glossary_terms": len(terms),
        })
        return {
            "project_id": stats.project_id,
            "translated": stats.translated,
            "reviewed": stats.reviewed,
            "files": stats.files,
            "members": stats.members,
            "glossary_terms": len(terms),
        }
