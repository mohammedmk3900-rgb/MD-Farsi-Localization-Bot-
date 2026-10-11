from __future__ import annotations
from typing import Any

class CommandCenterService:
    """Discord-oriented operational read model. No web UI or dashboard is required."""
    def __init__(self, application):
        self.application = application

    def status(self) -> dict[str, Any]:
        db_ok = self.application.health.database(self.application.store)
        health = self.application.health.evaluate({"database": "ok" if db_ok else "degraded", "translation": "ok", "glossary": "ok"})
        return {"service": "v11-genesis", "interface": "discord", "dashboard": False, "health": {"status": health.status, "checks": health.checks}, "tasks": self.application.tasks.summary(), "reviews": len(self.application.reviews.pending()), "glossary_terms": len(self.application.glossary.all()), "persistence": self.application.store.counts()}

    def render_discord(self) -> str:
        data = self.status()
        icon = "🟢" if data["health"]["status"] == "ok" else "🟡"
        task = data["tasks"]
        return (f"╔════════ MD Farsi Localization ════════╗\n{icon} V11 Genesis: {data['health']['status'].upper()}\n\n" f"📋 Tasks: {task['total']} | Review: {task['review_queue']}\n" f"🔎 Pending Reviews: {data['reviews']}\n" f"📖 Glossary Terms: {data['glossary_terms']}\n" f"🗃️ Events: {data['persistence']['events']}\n" f"🔄 Sync Runs: {data['persistence']['sync_runs']}\n" "🖥️ Dashboard: disabled\n╚═══════════════════════════════════════╝")

    def project_sync(self) -> dict[str, Any]:
        from app.integrations.paratranz import ParaTranzIntegration
        return self.application.sync.project(self.application, ParaTranzIntegration())