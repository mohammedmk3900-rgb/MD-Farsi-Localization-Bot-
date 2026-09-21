#!/usr/bin/env python3
"""Build the dashboard data from the same Command Center snapshot used by Discord."""
import json
from pathlib import Path

SNAPSHOT = Path("data/command_center.json")
OUTPUT = Path("dashboard/data/dashboard.json")

def main():
    if not SNAPSHOT.exists():
        raise SystemExit("data/command_center.json is missing; run command_center_snapshot.py first.")
    try:
        source = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Invalid Command Center snapshot: {exc}")
    required = ("project", "stats", "progress", "sections", "milestones", "updated_at")
    missing = [k for k in required if k not in source]
    if missing:
        raise SystemExit("Snapshot missing: " + ", ".join(missing))
    payload = {
        "schema": 3,
        "project": source["project"],
        "stats": source["stats"],
        "progress": source["progress"],
        "sections": source["sections"],
        "milestones": source["milestones"],
        "automation": source.get("automation", {}),
        "health": source.get("health", {}),
        "updated_at": source["updated_at"],
        "source": source.get("source", "ParaTranz API"),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Dashboard data written: {OUTPUT}")

if __name__ == "__main__":
    main()
