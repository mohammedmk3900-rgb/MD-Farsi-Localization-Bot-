#!/usr/bin/env python3
"""Sync ParaTranz project Terms into the Discord Persian glossary channel."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_BASE = "https://paratranz.cn/api"
PROJECT_ID = int(os.getenv("PARATRANZ_PROJECT_ID", "19621"))
TOKEN = os.getenv("PARATRANZ_TOKEN", "").strip()
WEBHOOK = os.getenv("DISCORD_GLOSSARY_WEBHOOK_URL", "").strip()
STATE = "data/glossary.json"
MESSAGE_STATE = "data/discord_messages.json"
OFFICIAL_DOC = "data/glossary_official.md"
MAX_ENTRIES = int(os.getenv("GLOSSARY_MAX_ENTRIES", "5000"))
PAGE_SIZE = 1000


def fail(message: str) -> None:
    print("ERROR: " + message, file=sys.stderr)
    raise SystemExit(1)


def request_json(method: str, url: str):
    headers = {
        "Accept": "application/json",
        "User-Agent": "MD-Farsi-Localization-Glossary/2.0",
        "Authorization": TOKEN,
    }
    req = Request(url, headers=headers, method=method)
    try:
        with urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"ParaTranz request failed: {exc}") from exc


def fetch_terms() -> list[dict]:
    if not TOKEN:
        raise RuntimeError("PARATRANZ_TOKEN is not set.")

    entries: list[dict] = []
    page = 1

    while len(entries) < MAX_ENTRIES:
        data = request_json(
            "GET",
            f"{API_BASE}/projects/{PROJECT_ID}/terms?page={page}&pageSize={PAGE_SIZE}",
        )

        if isinstance(data, list):
            batch = data
            page_count = None
        elif isinstance(data, dict):
            batch = data.get("results") or data.get("items") or data.get("data") or []
            page_count = data.get("pageCount")
        else:
            batch = []
            page_count = None

        if not isinstance(batch, list) or not batch:
            break

        for item in batch:
            if not isinstance(item, dict):
                continue
            term = str(item.get("term") or "").strip()
            translation = str(item.get("translation") or "").strip()
            if not term or not translation:
                continue
            entries.append({
                "id": item.get("id"),
                "source": term,
                "target": translation,
                "note": str(item.get("note") or "").strip(),
                "updated_at": item.get("updatedAt"),
                "variants": item.get("variants") or [],
            })

        if page_count is not None and page >= int(page_count):
            break
        if len(batch) < PAGE_SIZE:
            break
        page += 1

    if not entries:
        raise RuntimeError(f"No ParaTranz Terms found for project {PROJECT_ID}.")

    unique = {}
    for entry in entries:
        unique[entry["source"].casefold()] = entry

    return sorted(unique.values(), key=lambda x: x["source"].casefold())[:MAX_ENTRIES]


def load_json(path: str, default):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError, TypeError, ValueError):
        return default


def save_json(path: str, value) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(tmp, path)


def discord(method: str, url: str, payload: dict):
    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "MD-Farsi-Localization-Glossary/2.0",
        },
        method=method,
    )
    with urlopen(request, timeout=30) as response:
        raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def official_embeds() -> list[dict]:
    try:
        with open(OFFICIAL_DOC, encoding="utf-8") as handle:
            text = handle.read().strip()
    except FileNotFoundError:
        raise RuntimeError(f"Missing official glossary document: {OFFICIAL_DOC}")

    chunks = []
    current = []
    current_len = 0

    for paragraph in re.split(r"\n\s*\n", text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        addition = len(paragraph) + (2 if current else 0)
        if current and current_len + addition > 3800:
            chunks.append("\n\n".join(current))
            current = [paragraph]
            current_len = len(paragraph)
        else:
            current.append(paragraph)
            current_len += addition

    if current:
        chunks.append("\n\n".join(current))

    if len(chunks) > 10:
        raise RuntimeError("Official glossary document requires more than 10 Discord embeds.")

    return [
        {
            "title": (
                "📚 واژه‌نامهٔ رسمی ترجمهٔ فارسی Millennium Dawn"
                if index == 0
                else f"📚 واژه‌نامهٔ رسمی • بخش {index + 1}"
            ),
            "description": chunk,
        }
        for index, chunk in enumerate(chunks)
    ]


def live_embed(entries: list[dict]) -> dict:
    now = datetime.now(timezone.utc)
    digest = hashlib.sha256(
        json.dumps(entries, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:12]

    lines = [f"**{x['source']}** → {x['target']}" for x in entries[:35]]
    if len(entries) > 35:
        lines.append(f"… و **{len(entries) - 35:,}** اصطلاح دیگر")

    return {
        "author": {"name": "MD FARSI LOCALIZATION • COMMAND CENTER"},
        "title": "📖 واژه‌نامهٔ زنده • ParaTranz Terms",
        "description": (
            "این فهرست مستقیماً از بخش **Terms** پروژه ParaTranz "
            f"#{PROJECT_ID} دریافت می‌شود.\n\n" + "\n".join(lines)
        ),
        "fields": [
            {"name": "📚 تعداد Terms", "value": f"**{len(entries):,}**", "inline": True},
            {"name": "🔐 Snapshot", "value": digest, "inline": True},
            {"name": "🔄 Sync", "value": "خودکار • هر ۶ ساعت", "inline": True},
        ],
        "footer": {
            "text": f"ParaTranz Project {PROJECT_ID} • {now.strftime('%Y-%m-%d %H:%M UTC')}"
        },
        "timestamp": now.isoformat(),
    }


def upsert_message(state: dict, key: str, payload: dict) -> None:
    message_id = str(state.get(key, "")).strip()

    if message_id:
        try:
            discord("PATCH", f"{WEBHOOK}/messages/{message_id}", payload)
            return
        except HTTPError as exc:
            if exc.code != 404:
                raise

    result = discord("POST", WEBHOOK + "?wait=true", payload)
    new_id = str(result.get("id") or "")
    if not new_id:
        raise RuntimeError(f"Discord did not return a message ID for {key}.")
    state[key] = new_id


def main() -> None:
    if not WEBHOOK:
        fail("DISCORD_GLOSSARY_WEBHOOK_URL is not set.")

    entries = fetch_terms()
    old = load_json(STATE, {})
    old_entries = old.get("entries", []) if isinstance(old, dict) else []
    state = load_json(MESSAGE_STATE, {})
    if not isinstance(state, dict):
        state = {}

    if entries != old_entries:
        save_json(
            STATE,
            {
                "schema": 2,
                "source": f"{API_BASE}/projects/{PROJECT_ID}/terms",
                "project_id": PROJECT_ID,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "entries": entries,
            },
        )

    upsert_message(
        state,
        "glossary_official",
        {
            "username": "MD Farsi Localization • Command Center",
            "embeds": official_embeds(),
        },
    )
    upsert_message(
        state,
        "glossary",
        {
            "username": "MD Farsi Localization • Command Center",
            "embeds": [live_embed(entries)],
        },
    )

    save_json(MESSAGE_STATE, state)
    print(f"ParaTranz Terms synced: {len(entries):,} entries")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, HTTPError, URLError) as exc:
        fail(str(exc))
