from fastapi import FastAPI, HTTPException

from app.application import application
from app.services.achievements import AchievementService
from app.services.commands import CommandService
from app.services.dashboard import DashboardService
from app.services.glossary import GlossaryService
from app.services.reports import ReportService
from app.services.sync import sync_project

app = FastAPI(
    title="MD Farsi Localization Platform",
    version="2.1.0",
    description="Unified MD news application API.",
)

commands = CommandService()
achievements = AchievementService()
reports = ReportService()
dashboard = DashboardService()


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "application": "md-news",
        "database": application.context.settings.database_path,
    }


@app.get("/api/v1/project")
def project() -> dict:
    try:
        return sync_project()
    except Exception as exc:
        raise HTTPException(status_code=502, detail="ParaTranz synchronization failed") from exc


@app.get("/api/v1/glossary")
def glossary(page: int = 1, page_size: int = 100) -> dict:
    if page < 1 or page_size < 1 or page_size > 500:
        raise HTTPException(status_code=400, detail="Invalid pagination")
    try:
        items = GlossaryService(application.context.settings).page(page, page_size)
        return {"page": page, "page_size": page_size, "items": items}
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Glossary synchronization failed") from exc


@app.get("/api/v1/history")
def history(limit: int = 30) -> dict:
    return {"items": application.context.database.recent_snapshots(limit)}


@app.get("/api/v1/events")
def events(limit: int = 100) -> dict:
    return {"items": application.context.database.recent_events(limit)}


@app.get("/api/v1/dashboard")
def dashboard_contract() -> dict:
    snapshots = application.context.database.recent_snapshots(1)
    if not snapshots:
        return {"schema": 1, "project": None, "health": None, "discord": None}
    return dashboard.public_contract(snapshots[0]["payload"])


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
            "history": "SQLite snapshot/event store",
        },
        "discord_transport": "Bot API",
        "webhooks_required": False,
        "human_review_required": True,
    }
