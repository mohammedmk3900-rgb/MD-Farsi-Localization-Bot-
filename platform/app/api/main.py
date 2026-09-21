from fastapi import FastAPI, HTTPException

from app.config import settings
from app.persistence.database import Database
from app.services.command_center import CommandCenter

app = FastAPI(
    title="MD Farsi Localization Platform",
    version="1.0.0",
    description="Canonical API for project automation, analytics and Discord operations.",
)

database = Database(settings.database_path)
database.initialize()
command_center = CommandCenter(settings, database)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/snapshot")
def snapshot():
    try:
        return command_center.collect().model_dump(mode="json")
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Upstream collection failed") from exc
