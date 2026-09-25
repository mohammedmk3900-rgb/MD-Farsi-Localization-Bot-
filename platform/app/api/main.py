import json
import secrets
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware

from app.application import application
from app.services.commands import CommandService
from app.services.glossary import GlossaryService
from app.services.sync import sync_project

app = FastAPI(title="MD Farsi Localization Platform", version="2.3.0", description="Unified MD news application API.")

origins = [x.strip() for x in application.context.settings.cors_origins.split(",") if x.strip()]
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Accept", "Content-Type"],
    )

commands = CommandService()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "application": "md-news"}


@app.get("/ready")
def readiness() -> dict:
    """Verify the platform can read its operational database."""
    path = Path(application.context.settings.database_path)
    if not path.is_file():
        raise HTTPException(status_code=503, detail="Operational database is unavailable")
    try:
        with sqlite3.connect(path) as db:
            result = db.execute("PRAGMA integrity_check").fetchone()[0]
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="Operational database check failed") from exc
    if result != "ok":
        raise HTTPException(status_code=503, detail="Operational database integrity check failed")
    return {"status": "ready", "database": "ok"}


@app.get("/api/v1/project")
def project() -> dict:
    rows = application.context.database.recent_snapshots(50)
    for row in rows:
        if row["payload"].get("project"):
            return row["payload"]
    raise HTTPException(status_code=404, detail="No project snapshot available; run /api/v1/project/sync first")


@app.post("/api/v1/project/sync")
def project_sync(authorization: str | None = Header(default=None)) -> dict:
    token = application.context.settings.api_token
    if not token or not authorization or not secrets.compare_digest(authorization, f"Bearer {token}"):
        raise HTTPException(status_code=403, detail="Management API authorization required")
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
        "auto_publish": False,
        "sync_policy": "Only POST /api/v1/project/sync performs live synchronization",
    }


@app.get("/api/v1/operations/metrics")
def operation_metrics() -> dict:
    """Return safe aggregate counters for dashboards and uptime checks."""
    path = Path("data/last_run.json")
    if not path.is_file():
        return {"status": "unknown", "jobs": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Operation summary is unavailable") from exc
    jobs = payload.get("jobs", {}) if isinstance(payload, dict) else {}
    return {
        "status": payload.get("status", "unknown"),
        "generated_at": payload.get("generated_at"),
        "jobs_total": len(jobs),
        "jobs_ok": sum(1 for item in jobs.values() if isinstance(item, dict) and item.get("status") == "ok"),
        "jobs_failed": sum(1 for item in jobs.values() if isinstance(item, dict) and item.get("status") == "failed"),
        "jobs_skipped": sum(1 for item in jobs.values() if isinstance(item, dict) and item.get("status") == "skipped"),
    }


@app.get("/api/v1/operations/last")
def last_operation() -> dict:
    """Expose the last aggregate orchestration result without live side effects."""
    path = Path("data/last_run.json")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="No completed orchestration run available")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Operation summary is unavailable") from exc
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise HTTPException(status_code=503, detail="Operation summary schema is invalid")
    return data
