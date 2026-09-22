from __future__ import annotations

from app.services.scheduler import Scheduler


def build_manifest(scheduler: Scheduler) -> dict:
    return {
        "scheduler": "platform-core",
        "jobs": scheduler.manifest()["jobs"],
        "review_automation": False,
        "transport": "discord-bot-api",
        "webhooks": False,
    }
