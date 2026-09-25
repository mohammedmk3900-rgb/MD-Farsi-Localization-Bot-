"""Single entry point for all scheduled platform operations.

Each independent operation is isolated; invalid project data blocks dependent
reports without preventing Discord auditing or health diagnostics.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from app.services import jobs


def execute(*, daily: bool = False, weekly: bool = False) -> dict:
    results: dict[str, dict] = {}
    project_ok = False

    def run(name: str, action) -> None:
        nonlocal project_ok
        try:
            result = action()
            # The public run summary contains aggregates only. Never expose
            # raw Discord channel/role identifiers or other audit payloads.
            if name == "discord_audit":
                safe = {
                    "channels": result.get("server", {}).get("channels", 0),
                    "roles": result.get("server", {}).get("roles", 0),
                    "categories": result.get("server", {}).get("categories", 0),
                }
            elif name == "glossary":
                safe = {"count": result.get("count", 0)}
            elif name == "health":
                safe = {
                    "status": result.get("status", "unknown"),
                    "paratranz": bool(result.get("paratranz", False)),
                    "discord": bool(result.get("discord", False)),
                    "database": bool(result.get("database", False)),
                }
            elif name == "sync":
                project = result.get("project", {})
                safe = {
                    "project_id": project.get("project_id"),
                    "strings_total": project.get("strings_total"),
                    "translated": project.get("translated"),
                    "reviewed": project.get("reviewed"),
                }
            else:
                safe = {"period": result.get("period", name)}
            results[name] = {"status": "ok", "result": safe}
            if name == "sync":
                project_ok = True
        except Exception as exc:
            # Avoid logging exception messages: HTTP exceptions may contain
            # authorization URLs or private upstream response details.
            results[name] = {"status": "failed", "error_type": type(exc).__name__}

    run("sync", jobs.sync)
    run("glossary", jobs.glossary_sync)
    run("discord_audit", jobs.audit)
    run("health", jobs.health)

    if daily:
        if project_ok:
            run("daily_report", lambda: jobs.report("daily"))
        else:
            results["daily_report"] = {"status": "skipped", "reason": "project sync failed"}
    if weekly:
        if project_ok:
            run("weekly_report", lambda: jobs.report("weekly"))
        else:
            results["weekly_report"] = {"status": "skipped", "reason": "project sync failed"}

    status = "failed" if any(v["status"] == "failed" for v in results.values()) else "ok"
    summary = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "jobs": results,
    }
    path = Path("data/last_run.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Unified MD Farsi platform orchestrator")
    parser.add_argument("--daily", action="store_true")
    parser.add_argument("--weekly", action="store_true")
    args = parser.parse_args()
    summary = execute(daily=args.daily, weekly=args.weekly)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if summary["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
