"""Build, migrate and persist the Command Center single source of truth."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from ..config import Config
from ..models import ProjectStats, Snapshot
from ..state import load_json, save_json
from .progress import crossed, delta

SNAPSHOT_PATH = "data/command_center.json"
HISTORY_PATH = "data/discord_history.json"
RECORDS_PATH = "data/command_center_records.json"

def _previous() -> dict[str, Any]:
    data = load_json(SNAPSHOT_PATH, {})
    return data if isinstance(data, dict) else {}

def build(config: Config, stats: ProjectStats, files: list[dict[str, Any]]) -> tuple[dict[str, Any], Snapshot]:
    old = _previous()
    old_stats = old.get("stats", {})
    old_progress = old.get("progress", {})
    previous = {
        "translated": old_stats.get("translated", old_progress.get("translated", stats.translated)),
        "reviewed": old_stats.get("reviewed", old_progress.get("reviewed", stats.reviewed)),
        "translation_percent": old_progress.get("translation_percent", old_stats.get("translation_percent", stats.translation_percent)),
        "review_percent": old_progress.get("review_percent", old_stats.get("review_percent", stats.review_percent)),
    }
    now = datetime.now(timezone.utc)
    d = delta(stats, previous)
    milestones = crossed(float(previous["translation_percent"]), stats.translation_percent)

    history_doc = load_json(HISTORY_PATH, {})
    history = history_doc.get("snapshots", []) if isinstance(history_doc, dict) else []
    record = Snapshot(now.isoformat(), int(now.timestamp()), stats, d, milestones).to_dict()
    if history and history[-1].get("timestamp", "")[:16] == record["timestamp"][:16]:
        history[-1] = record
    else:
        history.append(record)
    history = history[-config.history_limit:]

    records = load_json(RECORDS_PATH, {})
    records = records if isinstance(records, dict) else {}
    records.update({
        "best_delta_translated": max(int(records.get("best_delta_translated", 0)), d.translated),
        "best_delta_reviewed": max(int(records.get("best_delta_reviewed", 0)), d.reviewed),
        "best_delta_translation_percent": max(float(records.get("best_delta_translation_percent", 0)), d.translation_percent),
        "best_delta_review_percent": max(float(records.get("best_delta_review_percent", 0)), d.review_percent),
        "sync_count": int(records.get("sync_count", 0)) + 1,
        "updated_at": now.isoformat(),
    })

    sections: dict[str, dict[str, Any]] = {}
    for item in files:
        name = str(item.get("name") or item.get("path") or "unknown")
        section = name.split("/", 1)[0]
        bucket = sections.setdefault(section, {"files": 0, "strings": 0, "translated": 0, "reviewed": 0, "words": 0})
        bucket["files"] += 1
        bucket["strings"] += int(item.get("total") or 0)
        bucket["translated"] += int(item.get("translated") or 0)
        bucket["reviewed"] += int(item.get("reviewed") or 0)
        bucket["words"] += int(item.get("words") or 0)
    for bucket in sections.values():
        total = bucket["strings"]
        bucket["translation_percent"] = round(bucket["translated"] / total * 100, 2) if total else 0.0
        bucket["review_percent"] = round(bucket["reviewed"] / total * 100, 2) if total else 0.0

    payload = {
        "schema": 6,
        "timestamp": now.isoformat(),
        "updated_at": now.isoformat(),
        "project": {"name": "Millennium Dawn Farsi Localization", "id": config.project_id, "url": config.project_url, "participants": config.participants},
        "stats": {**stats.to_dict(), "translation_percent": stats.translation_percent, "review_percent": stats.review_percent},
        "project_stats": stats.to_dict(),
        "progress": {"translation_percent": stats.translation_percent, "review_percent": stats.review_percent, "translated": stats.translated, "reviewed": stats.reviewed, **d.to_dict()},
        "history": {"count": len(history), "max": config.history_limit, "latest_epoch": int(now.timestamp())},
        "records": records,
        "sections": sections,
        "milestones": [{"threshold": n, "icon": i, "label": l} for n, i, l in (
            (1, "🎉", "اولین ۱٪"), (10, "🌱", "۱۰٪"), (25, "📈", "۲۵٪"), (50, "🔥", "۵۰٪"), (75, "🚀", "۷۵٪"), (100, "🏁", "۱۰۰٪")
        )],
        "milestones_crossed": milestones,
        "health": old.get("health", {"status": "pending", "percentage": 0, "passed_checks": 0, "total_checks": 0, "checks": {}, "updated_at": None}),
        "automation": {"interval_hours": config.sync_hours, "engine": "GitHub Actions", "last_sync": now.isoformat(), "mode": "scheduled", "timezone": "UTC"},
        "previous_progress_percent": float(previous["translation_percent"]),
        "previous_review_percent": float(previous["review_percent"]),
        "source": "ParaTranz API",
    }
    save_json(SNAPSHOT_PATH, payload)
    save_json(RECORDS_PATH, records)
    save_json(HISTORY_PATH, {"schema": 3, "project_id": config.project_id, "snapshots": history})
    return payload, Snapshot(now.isoformat(), int(now.timestamp()), stats, d, milestones)
