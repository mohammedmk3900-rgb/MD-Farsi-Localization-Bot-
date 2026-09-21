#!/usr/bin/env python3
"""Sync ParaTranz project Terms into a versioned Discord Persian glossary."""
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
PAGE_CHAR_LIMIT = 3600

STATUS_LABELS = {
    "fixed": "🟢 ثابت", "approved": "🟢 ثابت", "active": "🟢 ثابت",
    "review": "🟡 در حال بررسی", "reviewing": "🟡 در حال بررسی",
    "pending": "🟡 در حال بررسی",
    "proposed": "🔵 پیشنهادی", "suggested": "🔵 پیشنهادی", "draft": "🔵 پیشنهادی",
    "deprecated": "🔴 منسوخ", "obsolete": "🔴 منسوخ",
    "deprecated_term": "🔴 منسوخ",
}

def fail(message: str) -> None:
    print("ERROR: " + message, file=sys.stderr)
    raise SystemExit(1)

def request_json(method: str, url: str, payload: dict | None = None):
    headers = {"Accept": "application/json", "User-Agent": "MD-Farsi-Localization-Glossary/6.0"}
    if method != "GET":
        headers["Content-Type"] = "application/json"
    if TOKEN:
        headers["Authorization"] = TOKEN
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"Request failed: {exc}") from exc

def fetch_terms() -> list[dict]:
    if not TOKEN:
        raise RuntimeError("PARATRANZ_TOKEN is not set.")
    entries: list[dict] = []
    page = 1
    while len(entries) < MAX_ENTRIES:
        data = request_json("GET", f"{API_BASE}/projects/{PROJECT_ID}/terms?page={page}&pageSize={PAGE_SIZE}")
        if isinstance(data, list):
            batch, page_count = data, None
        elif isinstance(data, dict):
            batch = data.get("results") or data.get("items") or data.get("data") or []
            page_count = data.get("pageCount")
        else:
            batch, page_count = [], None
        if not isinstance(batch, list) or not batch:
            break
        for item in batch:
            if not isinstance(item, dict):
                continue
            term = str(item.get("term") or "").strip()
            translation = str(item.get("translation") or "").strip()
            if not term or not translation:
                continue
            raw_status = item.get("status") or item.get("state") or item.get("reviewStatus") or item.get("termStatus") or ""
            status_key = str(raw_status).strip().casefold().replace(" ", "_")
            entries.append({
                "id": item.get("id"),
                "source": term,
                "target": translation,
                "status": STATUS_LABELS.get(status_key, "🟡 در حال بررسی"),
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
    unique: dict[str, dict] = {}
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

def discord(method: str, url: str, payload: dict | None = None):
    return request_json(method, url, payload)

def discord_delete(url: str) -> None:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "MD-Farsi-Localization-Glossary/3.0"}, method="DELETE")
    try:
        with urlopen(request, timeout=30):
            return
    except HTTPError as exc:
        if exc.code != 404:
            raise

def official_embeds() -> list[dict]:
    try:
        with open(OFFICIAL_DOC, encoding="utf-8") as handle:
            text = handle.read().strip()
    except FileNotFoundError:
        raise RuntimeError(f"Missing official glossary document: {OFFICIAL_DOC}")
    chunks, current, current_len = [], [], 0
    for paragraph in re.split(r"\n\s*\n", text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        addition = len(paragraph) + (2 if current else 0)
        if current and current_len + addition > 3800:
            chunks.append("\n\n".join(current))
            current, current_len = [paragraph], len(paragraph)
        else:
            current.append(paragraph)
            current_len += addition
    if current:
        chunks.append("\n\n".join(current))
    if len(chunks) > 10:
        raise RuntimeError("Official glossary document requires more than 10 Discord embeds.")
    return [{
        "title": "📚 واژه‌نامهٔ رسمی ترجمهٔ فارسی Millennium Dawn" if index == 0 else f"📚 واژه‌نامهٔ رسمی • بخش {index + 1}",
        "description": chunk,
    } for index, chunk in enumerate(chunks)]

def glossary_version(old: dict, entries: list[dict], now: datetime) -> tuple[str, bool, str]:
    old_entries = old.get("entries", [])
    old_version = str(old.get("version", "1.0.0"))
    last_version_at = str(old.get("version_updated_at", old.get("updated_at", "")))
    try:
        major, minor, patch = (int(part) for part in old_version.split("."))
    except ValueError:
        major, minor, patch = 1, 0, 0
    terms_changed = entries != old_entries
    month_changed = False
    if last_version_at:
        try:
            previous = datetime.fromisoformat(last_version_at.replace("Z", "+00:00"))
            month_changed = (previous.year, previous.month) != (now.year, now.month)
        except ValueError:
            pass
    if terms_changed or month_changed:
        patch += 1
        if terms_changed and month_changed:
            reason = "تغییر اصطلاحات + شروع ماه جدید"
        elif terms_changed:
            reason = "تغییر اصطلاحات"
        else:
            reason = "شروع ماه جدید"
        return f"{major}.{minor}.{patch}", True, reason
    return f"{major}.{minor}.{patch}", False, "بدون تغییر"

def term_lines(entries: list[dict]) -> list[str]:
    lines = []
    for entry in entries:
        line = f"{entry.get('status', '🟢 ثابت')}  **{entry['source']}** → {entry['target']}"
        note = str(entry.get("note") or "").strip()
        if note:
            line += f"\n> _{note[:180]}_"
        lines.append(line)
    return lines

def live_embeds(entries: list[dict], version: str, changed_reason: str) -> list[dict]:
    now = datetime.now(timezone.utc)
    digest = hashlib.sha256(json.dumps(entries, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    pages, current, current_len = [], [], 0
    for line in term_lines(entries):
        addition = len(line) + (1 if current else 0)
        if current and current_len + addition > PAGE_CHAR_LIMIT:
            pages.append(current)
            current, current_len = [line], len(line)
        else:
            current.append(line)
            current_len += addition
    if current:
        pages.append(current)
    total_pages = max(1, len(pages))
    embeds = []
    for index, page_lines in enumerate(pages, start=1):
        embeds.append({
            "author": {"name": "MD FARSI LOCALIZATION • COMMAND CENTER"},
            "title": f"📖 اصطلاحات رسمی MD Farsi • v{version} • صفحه {index}/{total_pages}",
            "description": "مرجع زندهٔ اصطلاحات از **ParaTranz Terms** — Project #"
                + str(PROJECT_ID) + "\n\n" + "\n".join(page_lines),
            "fields": (
                [
                    {"name": "📚 تعداد Terms", "value": f"**{len(entries):,}**", "inline": True},
                    {"name": "🔢 نسخه", "value": f"v{version}", "inline": True},
                    {"name": "🔄 تغییر", "value": changed_reason, "inline": True},
                    {"name": "🔐 Snapshot", "value": digest, "inline": True},
                ] if index == total_pages else []
            ),
            "footer": {"text": f"ParaTranz Project {PROJECT_ID} • Sync خودکار • {now.strftime('%Y-%m-%d %H:%M UTC')}"},
        })
    return embeds

def upsert_message(state: dict, key: str, payload: dict) -> str:
    message_id = str(state.get(key, "")).strip()
    if message_id:
        try:
            discord("PATCH", f"{WEBHOOK}/messages/{message_id}", payload)
            return message_id
        except HTTPError as exc:
            if exc.code != 404:
                raise
    result = discord("POST", WEBHOOK + "?wait=true", payload)
    new_id = str(result.get("id") or "")
    if not new_id:
        raise RuntimeError(f"Discord did not return a message ID for {key}.")
    state[key] = new_id
    return new_id

def upsert_pages(state: dict, pages: list[dict]) -> None:
    previous = state.get("glossary_terms_pages", [])
    if not isinstance(previous, list):
        previous = []
    if not previous and state.get("glossary"):
        previous = [str(state["glossary"])]
    current_ids = []
    for index, embed in enumerate(pages):
        key = f"glossary_terms_{index + 1}"
        state[key] = previous[index] if index < len(previous) else ""
        current_ids.append(upsert_message(state, key, {
            "username": "MD Farsi Localization • Command Center",
            "embeds": [embed],
        }))
    for stale_id in previous[len(current_ids):]:
        if stale_id:
            discord_delete(f"{WEBHOOK}/messages/{stale_id}")
    state["glossary_terms_pages"] = current_ids
    state["glossary"] = current_ids[0] if current_ids else ""

def main() -> None:
    if not WEBHOOK:
        fail("DISCORD_GLOSSARY_WEBHOOK_URL is not set.")
    entries = fetch_terms()
    old = load_json(STATE, {})
    if not isinstance(old, dict):
        old = {}
    now = datetime.now(timezone.utc)
    version, version_changed, reason = glossary_version(old, entries, now)
    save_json(STATE, {
        "schema": 3,
        "source": f"{API_BASE}/projects/{PROJECT_ID}/terms",
        "project_id": PROJECT_ID,
        "version": version,
        "version_changed": version_changed,
        "version_change_reason": reason,
        "updated_at": now.isoformat(),
        "version_updated_at": now.isoformat() if version_changed or not old.get("version_updated_at") else old.get("version_updated_at"),
        "terms_changed": entries != old.get("entries", []),
        "entries": entries,
    })
    state = load_json(MESSAGE_STATE, {})
    if not isinstance(state, dict):
        state = {}
    upsert_message(state, "glossary_official", {
        "username": "MD Farsi Localization • Command Center",
        "embeds": official_embeds(),
    })
    upsert_pages(state, live_embeds(entries, version, reason))
    save_json(MESSAGE_STATE, state)
    print(f"ParaTranz Terms synced: {len(entries):,} entries • v{version} • {reason} • pages={len(state['glossary_terms_pages'])}")

if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, HTTPError, URLError) as exc:
        fail(str(exc))
