from fastapi import FastAPI, HTTPException

from app.application import application
from app.services.achievements import AchievementService
from app.services.analytics import AnalyticsService
from app.services.commands import CommandService
from app.services.glossary import GlossaryService
from app.services.health import HealthService
from app.services.reports import ReportService
from app.services.sync import sync_project

app = FastAPI(
    title="MD Farsi Localization Platform",
    version="2.0.0",
    description="Unified application API. Discord webhooks are not part of the core architecture.",
)

commands = CommandService()
analytics = AnalyticsService()
health_service = HealthService()
achievements = AchievementService()
reports = ReportService()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "application": "md-news", "database": application.context.settings.database_path}


@app.get("/api/v1/project")
def project() -> dict:
    try:
        return sync_project()
    except Exception as exc:
        raise HTTPException(status_code=502, detail="ParaTranz synchronization failed") from exc


@app.get("/api/v1/glossary")
def glossary(page: int = 1, page_size: int = 100) -> dict:
    try:
        items = GlossaryService(application.context.settings).page(page, page_size)
        return {"page": page, "page_size": page_size, "items": items}
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Glossary synchronization failed") from exc


@app.get("/api/v1/commands")
def command_contract() -> dict:
    return {"commands": commands.help()}


@app.get("/api/v1/architecture")
def architecture() -> dict:
    return {
        "application": "MD news",
        "core": "platform",
        "sources_of_truth": {
            "translations": "ParaTranz",
            "glossary": "ParaTranz Terms",
            "history": "SQLite event store",
        },
        "discord_transport": "Bot API",
        "webhooks_required": False,
        "human_review_required": True,
    }
