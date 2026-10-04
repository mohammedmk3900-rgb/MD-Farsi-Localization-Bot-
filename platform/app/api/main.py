import json
import secrets
import sqlite3
from contextlib import asynccontextmanager
from threading import Event, Thread
from pathlib import Path

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware

from app.application import application
from app.services.commands import CommandService
from app.services.glossary import GlossaryService
from app.services.sync import sync_project
from app.services.scheduler import build_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event = Event()
    scheduler_thread = None
    if application.context.settings.scheduler_embedded:
        scheduler = build_scheduler()
        scheduler_thread = Thread(
            target=scheduler.run_forever,
            args=(stop_event,),
            name="md-farsi-scheduler",
            daemon=True,
        )
        scheduler_thread.start()
    try:
        yield
    finally:
        if scheduler_thread is not None:
            stop_event.set()
            scheduler_thread.join(timeout=max(5, application.context.settings.scheduler_poll_seconds + 2))


app = FastAPI(title="MD Farsi Localization Platform", version="2.3.0", description="Unified MD Farsi Localization platform API.", lifespan=lifespan)

origins = [x.strip() for x in application.context.settings.cors_origins.split(",") if x.strip()]
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Accept", "Content-Type", "Authorization"],
    )

commands = CommandService()


def _require_management(authorization: str | None) -> None:
    token = application.context.settings.api_token
    if not token or not authorization or not secrets.compare_digest(authorization, f"Bearer {token}"):
        raise HTTPException(status_code=403, detail="Management API authorization required")


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
    _require_management(authorization)
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
        "automatic_discord_publication": True,
        "automatic_translation_approval": False,
        "automatic_assignment": False,
        "sync_policy": "Scheduler performs recurring synchronization; POST /api/v1/project/sync remains available for authorized manual runs",
    }


@app.get("/api/v1/operations/metrics")
def operation_metrics() -> dict:
    """Return safe aggregate counters for dashboards and uptime checks."""
    path = Path(application.context.settings.database_path).parent / "last_run.json"
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
    path = Path(application.context.settings.database_path).parent / "last_run.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="No completed orchestration run available")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Operation summary is unavailable") from exc
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise HTTPException(status_code=503, detail="Operation summary schema is invalid")
    return data

@app.get("/api/v1/scheduler")
def scheduler_status(authorization: str | None = Header(default=None)) -> dict:
    _require_management(authorization)
    scheduler = build_scheduler()
    jobs = scheduler.status()
    return {
        "status": "ok",
        "jobs": jobs,
        "jobs_total": len(jobs),
        "jobs_running": sum(1 for job in jobs if job["status"] == "running"),
        "jobs_failed": sum(1 for job in jobs if job["status"] == "failed"),
    }


@app.post("/api/v1/scheduler/{job_name}/run")
def scheduler_run(job_name: str, authorization: str | None = Header(default=None)) -> dict:
    _require_management(authorization)
    scheduler = build_scheduler()
    job = next((item for item in scheduler.jobs if item.name == job_name), None)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Unknown scheduler job: {job_name}")
    result = scheduler.run_now(job)
    if result["status"] == "locked":
        raise HTTPException(status_code=409, detail="Scheduler job is already running")
    if result["status"] == "failed":
        raise HTTPException(status_code=502, detail={"message": "Scheduler job failed", **result})
    return result
