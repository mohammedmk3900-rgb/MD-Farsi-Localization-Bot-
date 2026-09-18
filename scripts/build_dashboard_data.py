#!/usr/bin/env python3
"""Build dashboard/data/dashboard.json from the ParaTranz project API."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

PROJECT_ID = os.getenv("PARATRANZ_PROJECT_ID", "19621")
TOKEN = os.getenv("PARATRANZ_TOKEN")
PARTICIPANTS = int(os.getenv("PROJECT_PARTICIPANTS", "8"))
OUTPUT = Path("dashboard/data/dashboard.json")


def main():
    if not TOKEN:
        raise SystemExit("PARATRANZ_TOKEN is not set")

    request = Request(
        f"https://paratranz.cn/api/projects/{PROJECT_ID}/files",
        headers={
            "Accept": "application/json",
            "Authorization": TOKEN,
            "User-Agent": "MD-Farsi-Localization-Dashboard/1.0",
        },
    )
    with urlopen(request, timeout=30) as response:
        files = json.loads(response.read().decode("utf-8"))

    if not isinstance(files, list):
        raise SystemExit("Unexpected response from ParaTranz API")

    total = sum(int(item.get("total") or 0) for item in files)
    translated = sum(int(item.get("translated") or 0) for item in files)
    reviewed = sum(int(item.get("reviewed") or 0) for item in files)
    words = sum(int(item.get("words") or 0) for item in files)

    def percent(value):
        return round((value / total) * 100, 2) if total else 0

    payload = {
        "project": {
            "name": "Millennium Dawn Farsi Localization",
            "id": int(PROJECT_ID),
            "url": f"https://paratranz.cn/projects/{PROJECT_ID}",
            "participants": PARTICIPANTS,
        },
        "stats": {
            "files": len(files),
            "strings": total,
            "translated": translated,
            "reviewed": reviewed,
            "words": words,
            "translation_percent": percent(translated),
            "review_percent": percent(reviewed),
        },
        "sections": {},
        "milestones": [
            {"threshold": 1, "icon": "🎉", "label": "اولین ۱٪"},
            {"threshold": 10, "icon": "🌱", "label": "۱۰٪"},
            {"threshold": 25, "icon": "📈", "label": "۲۵٪"},
            {"threshold": 50, "icon": "🔥", "label": "۵۰٪"},
            {"threshold": 75, "icon": "🚀", "label": "۷۵٪"},
            {"threshold": 100, "icon": "🏁", "label": "۱۰۰٪"},
        ],
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": "ParaTranz API",
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Dashboard data written to {OUTPUT}")


if __name__ == "__main__":
    main()
