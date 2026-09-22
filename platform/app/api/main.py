from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.application import application
from app.services.commands import CommandService
from app.services.dashboard import DashboardService
from app.services.glossary import GlossaryService
from app.services.sync import sync_project

app = FastAPI(title="MD Farsi Localization Platform", version="2.2.0", description="Unified MD news application API.")

origins = [x.strip() for x in application.context.settings.cors_origins.split(",") if x.strip()]
if origins:
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Accept", "Content-Type"])

commands = CommandService()
dashboard = DashboardService()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "application": "md-news", "database": application.context.settings.database_path}


@app.get("/api/v1/project")
def project() -> dict:
    rows = application.context.database.recent_snapshots(50)
    for row in rows:
        if row["payload"].get("project"):
            return row["payload"]
    raise HTTPException(status_code=404, detail="No project snapshot available; run /api/v1/project/sync first")


@app.post("/api/v1/project/sync")
def project_sync() -> dict:
    try:
        return sync_project()
    except Exception as exc:
        raise HTTPException(status_code=502, detail="ParaTranz synchronization failed") from exc


@app.get("/api/v1/glossary")
def glossary(page: int = 1, page_size: int = 100) -> dict:
    if page < 1 or page_size < 1 or page_size > 500:
        raise HTTPException(status_code=400, detail="Invalid pagination")
    try:
        return {"page": page, "page_size": page_size, "items": GlossaryService(application.context.settings).page(page, page_size)}
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Glossary synchronization failed") from exc


@app.get("/api/v1/history")
def history(limit: int = 30) -> dict:
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="Invalid limit")
    return {"items": application.context.database.recent_snapshots(limit)}


@app.get("/api/v1/events")
def events(limit: int = 100) -> dict:
    if limit < 1 or limit > 1000:
        raise HTTPException(status_code=400, detail="Invalid limit")
    return {"items": application.context.database.recent_events(limit)}


@app.get("/api/v1/dashboard")
def dashboard_contract() -> dict:
    snapshots = application.context.database.recent_snapshots(50)
    for row in snapshots:
        if row["payload"].get("project"):
            return dashboard.public_contract(row["payload"])
    return {"schema": 1, "project": None, "health": None, "discord": None}


@app.get("/api/v1/commands")
def command_contract() -> dict:
    return {"commands": commands.help()}


@app.get("/api/v1/architecture")
def architecture() -> dict:
    return {"application": "MD news", "core": "platform", "sources_of_truth": {"translations": "ParaTranz", "glossary": "ParaTranz Terms", "history": "SQLite snapshot/event store"}, "discord_transport": "Bot API", "webhooks_required": False, "human_review_required": True, "sync_policy": "Only POST /api/v1/project/sync performs live synchronization"}
