#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API = "https://paratranz.cn/api"
PROJECT_ID = os.getenv("PARATRANZ_PROJECT_ID", "19621")
TOKEN = os.getenv("PARATRANZ_TOKEN")
WEBHOOK = os.getenv("DISCORD_ACHIEVEMENTS_WEBHOOK_URL")
VISUAL_URL = "https://raw.githubusercontent.com/mohammedmk3900-rgb/MD-Farsi-Localization-Bot-/main/assets/discord/achievement.svg"
STATE_FILE = "data/achievements.json"

MILESTONES = {
    1: ("🎉", "اولین ۱٪", "اولین نقطه عطف ترجمه ثبت شد!"),
    10: ("🌱", "۱۰٪ — آغاز جدی", "ده درصد مسیر ترجمه پشت سر گذاشته شد."),
    25: ("📈", "۲۵٪ — یک‌چهارم مسیر", "یک‌چهارم پروژه ترجمه شده است."),
    50: ("🔥", "۵۰٪ — نیمه راه", "پروژه به نیمه مسیر ترجمه رسید."),
    75: ("🚀", "۷۵٪ — نزدیک به پایان", "بخش بزرگی از ترجمه تکمیل شده است."),
    100: ("🏁", "۱۰۰٪ — تکمیل ترجمه", "ترجمه پروژه به پایان رسید."),
}

def fail(message):
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)

def request_json(url, method="GET", payload=None, auth=False):
    headers = {
        "Accept": "application/json",
        "User-Agent": "MD-Farsi-Localization-Achievements/2.0",
    }
    if auth:
        if not TOKEN:
            fail("PARATRANZ_TOKEN is not set.")
        headers["Authorization"] = TOKEN
    body = None
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    try:
        with urlopen(Request(url, data=body, headers=headers, method=method), timeout=30) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        fail(f"HTTP {exc.code}: {detail[:1000]}")
    except URLError as exc:
        fail(f"Network error: {exc}")

def get_stats():
    files = request_json(
        f"{API}/projects/{PROJECT_ID}/files",
        auth=True,
    )
    if not isinstance(files, list):
        fail("ParaTranz returned an unexpected files response.")
    total = sum(int(item.get("total") or 0) for item in files)
    translated = sum(int(item.get("translated") or 0) for item in files)
    percent = (translated / total * 100) if total else 0
    return total, translated, percent

def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as file:
            value = json.load(file)
        return {int(item) for item in value}
    except (FileNotFoundError, ValueError, TypeError):
        return set()

def save_state(announced):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as file:
        json.dump(sorted(announced), file, ensure_ascii=False, indent=2)
        file.write("\n")

def post_achievement(threshold, total, translated):
    icon, name, detail = MILESTONES[threshold]
    now = datetime.now(timezone.utc)
    payload = {
        "username": "MD Farsi Localization • Achievements",
        "embeds": [{
            "author": {"name": "MD Farsi Localization • Achievements"},
            "title": f"{icon} {name}",
            "url": "https://paratranz.cn/projects/19621",
            "image": {"url": VISUAL_URL},
            "description": (
                f"## {detail}\n\n"
                f"**Millennium Dawn Farsi Localization** به **{threshold}%** رسید! 🎮\n\n"
                f"📝 **{translated:,} / {total:,}** رشته ترجمه شده\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "💪 ادامه می‌دیم تا ۱۰۰٪!"
            ),
            "color": 0xF1C40F,
            "footer": {"text": "MD Farsi Localization • Achievement Unlocked"},
            "timestamp": now.isoformat(),
        }],
    }
    request_json(f"{WEBHOOK}?wait=true", method="POST", payload=payload)

def main():
    if not WEBHOOK:
        fail("DISCORD_ACHIEVEMENTS_WEBHOOK_URL is not set.")
    total, translated, percent = get_stats()
    announced = load_state()
    newly = [m for m in MILESTONES if percent >= m and m not in announced]

    for threshold in newly:
        post_achievement(threshold, total, translated)
        announced.add(threshold)

    save_state(announced)
    print(
        f"Progress: {percent:.2f}% | "
        f"Translated: {translated}/{total} | "
        f"New achievements: {len(newly)}"
    )

if __name__ == "__main__":
    main()
