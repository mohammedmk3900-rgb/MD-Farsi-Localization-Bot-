from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import uuid4

from app.domain.models import GlossaryTerm
from app.errors import StaleUpstreamError
from app.integrations.paratranz import ParaTranzIntegration

if TYPE_CHECKING:
    from app.services.application import GenesisApplication

class SyncService:
    """Synchronize authoritative ParaTranz data without destructive empty overwrites."""
    def project(self, app: GenesisApplication, integration: ParaTranzIntegration) -> dict:
        started = datetime.now(timezone.utc).isoformat()
        run_id = str(uuid4())
        project_id = integration.config.project_id
        try:
            stats = integration.stats()
            raw_terms = integration.glossary()
            if stats.project_id != project_id:
                raise StaleUpstreamError("ParaTranz project identity mismatch")
            if stats.strings_total <= 0:
                raise StaleUpstreamError("ParaTranz returned an invalid zero-string project")
            terms = [GlossaryTerm(source=str(x["source"]).strip(), target=str(x["target"]).strip(), status=str(x.get("status", "🟢 ثابت"))) for x in raw_terms if x.get("source") and x.get("target")]
            if raw_terms and not terms:
                raise StaleUpstreamError("ParaTranz glossary contained no valid terms")
            if not raw_terms and app.store.latest_glossary_snapshot(project_id):
                raise StaleUpstreamError("ParaTranz glossary is empty; existing snapshot was preserved")
            app.glossary.replace(terms)
            now = datetime.now(timezone.utc).isoformat()
            app.store.save_glossary_snapshot(project_id, now, raw_terms)
            payload = {"project_id": project_id, "translated": stats.translated, "reviewed": stats.reviewed, "files": stats.files, "members": stats.members, "glossary_terms": len(terms)}
            app.store.record_sync_run(run_id, project_id, started, "success", payload, now)
            app.audit("paratranz.sync", None, {"run_id": run_id, **payload})
            return {"run_id": run_id, **payload}
        except Exception as exc:
            app.store.record_sync_run(run_id, project_id, started, "failed", {"error_type": type(exc).__name__, "error": str(exc)}, datetime.now(timezone.utc).isoformat())
            app.audit("paratranz.sync.failed", None, {"run_id": run_id, "error_type": type(exc).__name__, "error": str(exc)})
            raise