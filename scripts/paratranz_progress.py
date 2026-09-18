#!/usr/bin/env python3

import json
import os
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PARATRANZ_BASE_URL = "https://paratranz.cn/api"
PROJECT_ID = os.getenv("PARATRANZ_PROJECT_ID", "19621")
PARATRANZ_TOKEN = os.getenv("PARATRANZ_TOKEN")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_PROGRESS_WEBHOOK_URL")
STATE_FILE = "data/discord_messages.json"
VISUAL_URL = "https://raw.githubusercontent.com/mohammedmk3900-rgb/MD-Farsi-Localization-Bot-/main/assets/discord/progress.svg"


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def http_json(url: str, method: str = "GET", headers=None, payload=None):
    request_headers = {
        "Accept": "application/json",
        "User-Agent": "Millennium-Dawn-Farsi-Localization-Progress/1.0",
    }
    if headers:
        request_headers.update(headers)

    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json"

    request = Request(url, data=body, headers=request_headers, method=method)

    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {response_body[:1000]}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON: {exc}") from exc


def get_stats():
    if not PARATRANZ_TOKEN:
        fail("PARATRANZ_TOKEN is not set.")

    files = http_json(
        f"{PARATRANZ_BASE_URL}/projects/{PROJECT_ID}/files",
        headers={"Authorization": PARATRANZ_TOKEN},
    )

    if not isinstance(files, list):
        fail("ParaTranz returned an unexpected files response.")

    total = sum(int(f.get("total") or 0) for f in files)
    translated = sum(int(f.get("translated") or 0) for f in files)
    reviewed = sum(int(f.get("reviewed") or 0) for f in files)

    percent = (translated / total * 100) if total else 0
    review_percent = (reviewed / total * 100) if total else 0

    return len(files), total, translated, reviewed, percent, review_percent


def progress_bar(percent: float, size: int = 20) -> str:
    filled = min(size, max(0, round(percent / 100 * size)))
    return "🟩" * filled + "⬜" * (size - filled)


def milestone(percent: float) -> tuple[str, str]:
    milestones = [
        (100, "🏁 فارسی‌سازی کامل", "پروژه به 100٪ ترجمه رسیده است."),
        (75, "🚀 75٪ — نزدیک به پایان", "بخش بزرگی از پروژه تکمیل شده است."),
        (50, "🔥 50٪ — نیمه راه", "پروژه به نیمه مسیر ترجمه رسیده است."),
        (25, "📈 25٪ — یک‌چهارم مسیر", "یک‌چهارم مسیر ترجمه پشت سر گذاشته شده است."),
        (10, "🌱 10٪ — آغاز مسیر", "اولین نقطه عطف بزرگ پروژه ثبت شده است."),
        (0, "🚀 شروع مسیر", "پروژه در حال پیشرفت است."),
    ]
    for threshold, title, description in milestones:
        if percent >= threshold:
            return title, description
    return milestones[-1][1], milestones[-1][2]


def load_message_id():
    try:
        with open(STATE_FILE, encoding="utf-8") as file:
            return str(json.load(file).get("progress", "")).strip()
    except (FileNotFoundError, ValueError, TypeError):
        return ""


def save_message_id(message_id: str):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    state = {"stats": "", "progress": ""}
    try:
        with open(STATE_FILE, encoding="utf-8") as file:
            state.update(json.load(file))
    except (FileNotFoundError, ValueError, TypeError):
        pass
    state["progress"] = str(message_id)
    with open(STATE_FILE, "w", encoding="utf-8") as file:
        json.dump(state, file, ensure_ascii=False, indent=2)
        file.write("\n")


def build_embed(stats):
    files, total, translated, reviewed, percent, review_percent = stats
    title, milestone_text = milestone(percent)
    now = datetime.now(timezone.utc)

    return {
        "author": {"name": "MD Farsi Localization • Progress"},
        "title": "📈 پیشرفت پروژه",
        "description": (
            "╭────────────────────────╮\n"
            "   **Millennium Dawn Farsi Localization**\n"
            "   وضعیت زنده پروژه از ParaTranz\n"
            "╰────────────────────────╯\n\n"
            f"{progress_bar(percent)}\n"
            f"### **{percent:.2f}%** ترجمه شده"
        ),
        "url": "https://paratranz.cn/projects/19621",
        "image": {"url": VISUAL_URL},
        "color": 0x2ECC71,
        "fields": [
            {
                "name": "🎯 نقطه فعلی",
                "value": f"**{title}**\n{milestone_text}",
                "inline": False,
            },
            {
                "name": "📝 ترجمه‌شده",
                "value": f"**{translated:,}** از **{total:,}** رشته",
                "inline": True,
            },
            {
                "name": "🔎 بازبینی‌شده",
                "value": f"**{reviewed:,}**\n{review_percent:.2f}%",
                "inline": True,
            },
            {
                "name": "📄 فایل‌ها",
                "value": f"**{files:,}**",
                "inline": True,
            },
        ],
        "footer": {
            "text": "MD Farsi Localization • Live Progress • ParaTranz"
        },
        "timestamp": now.isoformat(),
    }


def send_new(embed):
    if not DISCORD_WEBHOOK_URL:
        fail("DISCORD_PROGRESS_WEBHOOK_URL is not set.")

    separator = "&" if "?" in DISCORD_WEBHOOK_URL else "?"
    result = http_json(
        f"{DISCORD_WEBHOOK_URL}{separator}wait=true",
        method="POST",
        payload={"username": "MD Farsi Localization • Progress", "embeds": [embed]},
    )
    if not result or "id" not in result:
        fail("Discord did not return a message ID.")
    return str(result["id"])


def edit_existing(embed, message_id):
    if not DISCORD_WEBHOOK_URL or not message_id:
        return False

    try:
        http_json(
            f"{DISCORD_WEBHOOK_URL}/messages/{message_id}",
            method="PATCH",
            payload={"embeds": [embed]},
        )
        return True
    except RuntimeError as exc:
        print(f"Existing message unavailable; recreating it: {exc}")
        return False


def main():
    try:
        stats = get_stats()
        embed = build_embed(stats)
        discord_message_id = load_message_id()
        if edit_existing(embed, discord_message_id):
            message_id = discord_message_id
            save_message_id(message_id)
            print("Progress message updated successfully.")
        else:
            message_id = send_new(embed)
            save_message_id(message_id)
            print(f"Progress message created: {message_id}")

        output = os.getenv("GITHUB_OUTPUT")
        if output:
            with open(output, "a", encoding="utf-8") as f:
                f.write(f"message_id={message_id}\n")
    except RuntimeError as exc:
        fail(str(exc))


if __name__ == "__main__":
    main()
