#!/usr/bin/env python3

import json
import os
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


PARATRANZ_BASE_URL = "https://paratranz.cn/api"
PROJECT_ID = os.getenv("PARATRANZ_PROJECT_ID", "19621")

PARATRANZ_TOKEN = os.getenv("PARATRANZ_TOKEN")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
STATE_FILE = "data/discord_messages.json"
VISUAL_URL = "https://raw.githubusercontent.com/mohammedmk3900-rgb/MD-Farsi-Localization-Bot-/main/assets/discord/stats.svg"

# Your current real participant count.
# Change this when the project membership changes.
PARTICIPANTS = int(os.getenv("PROJECT_PARTICIPANTS", "8"))


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def http_json(
    url: str,
    method: str = "GET",
    headers: dict | None = None,
    payload: dict | None = None,
):
    request_headers = {
        "Accept": "application/json",
        "User-Agent": "Millennium-Dawn-Farsi-Localization-Stats/1.0",
    }

    if headers:
        request_headers.update(headers)

    body = None

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json"

    request = Request(
        url,
        data=body,
        headers=request_headers,
        method=method,
    )

    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")

            if not raw:
                return None

            return json.loads(raw)

    except HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        fail(
            f"HTTP {exc.code} from {url}\n"
            f"Response: {response_body[:1000]}"
        )

    except URLError as exc:
        fail(f"Network error while requesting {url}: {exc}")

    except json.JSONDecodeError as exc:
        fail(f"Invalid JSON returned by {url}: {exc}")


def get_paratranz_files():
    if not PARATRANZ_TOKEN:
        fail("PARATRANZ_TOKEN is not set.")

    url = f"{PARATRANZ_BASE_URL}/projects/{PROJECT_ID}/files"

    return http_json(
        url,
        headers={
            "Authorization": PARATRANZ_TOKEN,
        },
    )


def calculate_stats(files):
    if not isinstance(files, list):
        fail("ParaTranz returned an unexpected files response.")

    total_strings = 0
    translated_strings = 0
    reviewed_strings = 0
    total_words = 0

    for file_info in files:
        total_strings += int(file_info.get("total") or 0)
        translated_strings += int(file_info.get("translated") or 0)
        reviewed_strings += int(file_info.get("reviewed") or 0)
        total_words += int(file_info.get("words") or 0)

    file_count = len(files)

    translation_percent = (
        (translated_strings / total_strings) * 100
        if total_strings
        else 0
    )

    review_percent = (
        (reviewed_strings / total_strings) * 100
        if total_strings
        else 0
    )

    return {
        "files": file_count,
        "strings": total_strings,
        "translated": translated_strings,
        "reviewed": reviewed_strings,
        "words": total_words,
        "translation_percent": translation_percent,
        "review_percent": review_percent,
        "participants": PARTICIPANTS,
    }


def format_percent(value: float) -> str:
    # Keep useful precision without showing ugly floating-point noise.
    if value >= 1:
        return f"{value:.2f}%"

    if value >= 0.1:
        return f"{value:.2f}%"

    return f"{value:.2f}%"


def format_number(value: int) -> str:
    return f"{value:,}"


def load_message_id():
    try:
        with open(STATE_FILE, encoding="utf-8") as file:
            return str(json.load(file).get("stats", "")).strip()
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
    state["stats"] = str(message_id)
    with open(STATE_FILE, "w", encoding="utf-8") as file:
        json.dump(state, file, ensure_ascii=False, indent=2)
        file.write("\n")


def build_embed(stats):
    now = datetime.now(timezone.utc)
    translation = stats["translation_percent"]
    review = stats["review_percent"]

    def bar(percent, size=16):
        filled = min(size, max(0, round(percent / 100 * size)))
        return "🟦" * filled + "⬜" * (size - filled)

    return {
        "author": {"name": "MD Farsi Localization • Statistics"},
        "title": "📊 آمار پروژه",
        "url": "https://paratranz.cn/projects/19621",
        "image": {"url": VISUAL_URL},
        "description": (
            "╭────────────────────────╮\n"
            "   **Millennium Dawn Farsi Localization**\n"
            "   همگام‌سازی خودکار با ParaTranz\n"
            "╰────────────────────────╯\n\n"
            f"🌐 **ترجمه**  {format_percent(translation)}\n"
            f"{bar(translation)}\n\n"
            f"🔎 **بازبینی**  {format_percent(review)}\n"
            f"{bar(review)}"
        ),
        "color": 0x3498DB,
        "fields": [
            {
                "name": "📦 وضعیت پروژه",
                "value": (
                    f"**{format_number(stats['files'])}** فایل  •  "
                    f"**{format_number(stats['strings'])}** رشته\n"
                    f"**{format_number(stats['words'])}** کلمه  •  "
                    f"**{format_number(stats['participants'])}** مشارکت‌کننده"
                ),
                "inline": False,
            },
            {
                "name": "📄 فایل‌ها",
                "value": f"**{format_number(stats['files'])}**",
                "inline": True,
            },
            {
                "name": "📝 کل رشته‌ها",
                "value": f"**{format_number(stats['strings'])}**",
                "inline": True,
            },
            {
                "name": "🌐 ترجمه‌شده",
                "value": (
                    f"**{format_number(stats['translated'])}**\n"
                    f"{format_percent(stats['translation_percent'])}"
                ),
                "inline": True,
            },
            {
                "name": "🔎 بازبینی‌شده",
                "value": (
                    f"**{format_number(stats['reviewed'])}**\n"
                    f"{format_percent(stats['review_percent'])}"
                ),
                "inline": True,
            },
            {
                "name": "👥 مشارکت‌کنندگان",
                "value": f"**{format_number(stats['participants'])} نفر**",
                "inline": True,
            },
            {
                "name": "📚 کل کلمات",
                "value": f"**{format_number(stats['words'])}**",
                "inline": True,
            },
        ],
        "footer": {
            "text": "MD Farsi Localization • Auto Sync • ParaTranz"
        },
        "timestamp": now.isoformat(),
    }


def send_new_discord_message(embed):
    if not DISCORD_WEBHOOK_URL:
        fail("DISCORD_WEBHOOK_URL is not set.")

    # wait=true makes Discord return the created message,
    # including its message ID.
    separator = "&" if "?" in DISCORD_WEBHOOK_URL else "?"
    url = f"{DISCORD_WEBHOOK_URL}{separator}wait=true"

    payload = {
        "username": "ParaTranz Stats",
        "embeds": [embed],
    }

    return http_json(
        url,
        method="POST",
        payload=payload,
    )


def edit_discord_message(embed):
    if not DISCORD_WEBHOOK_URL:
        fail("DISCORD_WEBHOOK_URL is not set.")

    if not DISCORD_MESSAGE_ID:
        return None

    url = (
        f"{DISCORD_WEBHOOK_URL}"
        f"/messages/{discord_message_id}"
    )

    payload = {
        "embeds": [embed],
    }

    try:
        return http_json(
            url,
            method="PATCH",
            payload=payload,
        )

    except SystemExit:
        # If the stored message was deleted or became unavailable,
        # the workflow will recreate it.
        print(
            "Stored Discord message could not be edited. "
            "A new message will be created."
        )
        return None


def write_github_output(name: str, value: str):
    github_output = os.getenv("GITHUB_OUTPUT")

    if not github_output:
        return

    with open(github_output, "a", encoding="utf-8") as output:
        output.write(f"{name}={value}\n")


def main():
    print(f"Fetching ParaTranz project {PROJECT_ID}...")

    files = get_paratranz_files()
    stats = calculate_stats(files)
    embed = build_embed(stats)

    print(
        f"Files: {stats['files']}\n"
        f"Strings: {stats['strings']}\n"
        f"Translated: {stats['translated']} "
        f"({format_percent(stats['translation_percent'])})\n"
        f"Reviewed: {stats['reviewed']} "
        f"({format_percent(stats['review_percent'])})"
    )

    # Try editing the existing message first.
    discord_message_id = load_message_id()

    if discord_message_id:
        print(
            f"Updating Discord message {discord_message_id}..."
        )

        result = edit_discord_message(embed)

        if result is not None:
            print("Discord message updated successfully.")
            write_github_output(
                "message_id",
                discord_message_id,
            )
            save_message_id(discord_message_id)
            return

    # No message ID exists, or the old message could not be edited.
    print("Creating a new Discord stats message...")

    result = send_new_discord_message(embed)

    if not result or "id" not in result:
        fail(
            "Discord did not return a message ID. "
            "Make sure the webhook URL is correct."
        )

    message_id = str(result["id"])
    save_message_id(message_id)

    print(
        f"Discord stats message created: {message_id}"
    )

    write_github_output(
        "message_id",
        message_id,
    )


if __name__ == "__main__":
    main()
