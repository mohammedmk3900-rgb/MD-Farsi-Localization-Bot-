from __future__ import annotations

from datetime import datetime, timezone

from app.application import application
from app.services.achievements import AchievementService
from app.services.audit import DiscordAuditService
from app.services.command_center import CommandCenter
from app.services.discord_notifications import DiscordNotificationService
from app.services.reports import ReportService
from app.services.glossary import GlossaryService
from app.services.health import HealthService


def sync() -> dict:
    snapshot = CommandCenter(
        application.context.settings,
        application.context.database,
    ).collect()
    return snapshot.model_dump(mode="json")


def report(period: str = "daily") -> dict:
    rows = application.context.database.recent_snapshots(50)
    project = next((r["payload"].get("project") for r in rows if r["payload"].get("project")), None)
    if not project:
        raise RuntimeError("No persisted project snapshot is available")
    payload = ReportService().build({"project": project}, period=period)
    channel = application.context.settings.channel_reports
    if channel:
        DiscordNotificationService(application.context.settings).embed(
            channel,
            payload["title"],
            f"دوره: {period}\nترجمه: {project.get('translation_percent', 0):.2f}%\nبازبینی: {project.get('review_percent', 0):.2f}%\nرشته‌ها: {project.get('translated', 0):,}/{project.get('strings_total', 0):,}",
        )
    application.record("report.generated", payload)
    return payload


def glossary_sync() -> dict:
    result = GlossaryService(application.context.settings).sync_all()
    application.record("glossary.synced", {"count": len(result)})
    return {"count": len(result)}


def health() -> dict:
    settings = application.context.settings
    paratranz_ok = False
    discord_ok = False
    try:
        from app.integrations.paratranz import ParaTranzClient
        ParaTranzClient(settings).project_snapshot()
        paratranz_ok = True
    except Exception:
        pass
    try:
        from app.integrations.discord import DiscordClient
        DiscordClient(settings).snapshot()
        discord_ok = True
    except Exception:
        pass
    status = HealthService().check(
        paratranz=paratranz_ok,
        discord=discord_ok,
        database=True,
    ).model_dump(mode="json")
    application.record("health.checked", status)
    channel = settings.channel_health
    if channel:
        DiscordNotificationService(settings).embed(
            channel,
            "🛰️ سلامت سیستم • SYSTEM HEALTH",
            f"وضعیت: **{status['status']}**\nParaTranz: {'✅' if paratranz_ok else '❌'}\nDiscord: {'✅' if discord_ok else '❌'}\nDatabase: ✅",
        )
    return status


def audit() -> dict:
    payload = DiscordAuditService(application.context.settings).persist()
    application.record("discord.audit", {
        "generated_at": payload["generated_at"],
        "channels": payload["server"]["channels"],
        "roles": payload["server"]["roles"],
    })
    return payload
