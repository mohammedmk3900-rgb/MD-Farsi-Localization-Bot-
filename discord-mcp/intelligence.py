"""Deterministic project-intelligence engine for indexed Discord history.

Builds event-level signals from messages, replies, threads, and activity windows.
It is deliberately local-first and rule-based: no model calls, no publishing,
and no inference about private attributes.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

CATEGORY_MARKERS: dict[str, tuple[str, ...]] = {
    "واژه‌نامه": ("واژه‌نامه", "واژه نامه", "glossary", "terminology", "ترمینولوژی"),
    "بازبینی": ("بازبینی", "review", "reviewed", "اصلاح", "بررسی"),
    "ترجمه": ("ترجمه", "translation", "localization", "translated"),
    "مشکل": ("خطا", "error", "bug", "failed", "خراب", "مشکل", "ارور"),
    "همکاری": ("همکاری", "مترجم", "translator", "عضو", "member"),
    "پروژه": ("پروژه", "project", "آپدیت", "update", "نسخه", "release", "ربات", "bot"),
}

IMPORTANT_MARKERS = (
    "مهم", "فوری", "urgent", "announcement", "اعلام", "release", "نسخه",
    "خطا", "error", "bug", "failed", "خراب",
)
FOLLOWUP_MARKERS = (
    "؟", "?", "لطفاً", "لطفا", "باید", "نیاز", "میشه", "میشود", "بررسی کنید",
    "please", "need", "todo", "تسک", "task", "منتظر",
)


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\u200c", " ")).strip()


def category(content: str) -> str:
    lowered = content.casefold()
    for name, markers in CATEGORY_MARKERS.items():
        if any(marker.casefold() in lowered for marker in markers):
            return name
    return "عمومی"


def important(content: str) -> bool:
    lowered = content.casefold()
    return any(marker.casefold() in lowered for marker in IMPORTANT_MARKERS)


def followup(content: str) -> bool:
    lowered = content.casefold()
    return any(marker.casefold() in lowered for marker in FOLLOWUP_MARKERS)


class DiscordIntelligence:
    def __init__(self, db_path: str | Path) -> None:
        self.path = str(db_path)

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        return db

    def _messages(self, db: sqlite3.Connection, start: datetime, end: datetime) -> list[dict[str, Any]]:
        rows = db.execute(
            """
            SELECT id, channel_id, channel_name, author_id, author_name, content,
                   timestamp, edited_timestamp, url, reference_message_id,
                   reference_channel_id, thread_id, message_type
            FROM messages
            WHERE deleted=0 AND timestamp IS NOT NULL
            ORDER BY timestamp ASC
            """
        ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            timestamp = parse_time(row["timestamp"])
            if timestamp is None or timestamp < start or timestamp > end:
                continue
            content = normalize(row["content"] or "")
            if not content:
                continue
            item = dict(row)
            item["timestamp_dt"] = timestamp
            item["content"] = content
            item["category"] = category(content)
            item["important"] = important(content)
            item["followup"] = followup(content)
            result.append(item)
        return result

    @staticmethod
    def _event_key(message: dict[str, Any], first_seen: dict[str, datetime]) -> str:
        thread_id = message.get("thread_id")
        if thread_id:
            return f"thread:{thread_id}"
        reference_id = message.get("reference_message_id")
        if reference_id:
            return f"reply:{reference_id}"
        channel_id = message.get("channel_id") or "unknown"
        stamp = message["timestamp_dt"]
        bucket = stamp - timedelta(minutes=stamp.minute % 30, seconds=stamp.second, microseconds=stamp.microsecond)
        return f"channel:{channel_id}:{bucket.isoformat()}"

    def _events(self, messages: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for message in messages:
            groups[self._event_key(message, {})].append(message)

        events: list[dict[str, Any]] = []
        for key, items in groups.items():
            categories = Counter(item["category"] for item in items)
            participants = {
                item["author_name"] for item in items if item.get("author_name")
            }
            unresolved = [
                item for item in items
                if item["followup"] and not any(
                    reply.get("reference_message_id") == item["id"]
                    for reply in messages
                )
            ]
            score = (
                len(items)
                + len(participants)
                + sum(2 for item in items if item["important"])
                + sum(2 for item in items if item.get("reference_message_id"))
                + len(unresolved)
            )
            ordered = sorted(items, key=lambda item: item["timestamp_dt"])
            events.append({
                "event_id": key,
                "category": categories.most_common(1)[0][0],
                "category_counts": dict(categories),
                "message_count": len(items),
                "participant_count": len(participants),
                "participants": sorted(participants)[:20],
                "started_at": ordered[0]["timestamp"],
                "last_activity_at": ordered[-1]["timestamp"],
                "important": any(item["important"] for item in items),
                "reply_count": sum(1 for item in items if item.get("reference_message_id")),
                "unresolved_followups": [
                    {
                        "id": item["id"],
                        "author": item.get("author_name"),
                        "content": item["content"][:400],
                        "url": item.get("url"),
                    }
                    for item in unresolved[:10]
                ],
                "samples": [
                    {
                        "id": item["id"],
                        "author": item.get("author_name"),
                        "content": item["content"][:300],
                        "timestamp": item["timestamp"],
                        "url": item.get("url"),
                    }
                    for item in ordered[-3:]
                ],
                "score": score,
            })

        events.sort(key=lambda item: (item["score"], item["last_activity_at"]), reverse=True)
        return events[: max(1, min(limit, 50))]

    @staticmethod
    def _metrics(messages: list[dict[str, Any]]) -> dict[str, Any]:
        categories = Counter(item["category"] for item in messages)
        channels = Counter(item.get("channel_name") or item.get("channel_id") for item in messages)
        authors = Counter(item.get("author_name") for item in messages if item.get("author_name"))
        return {
            "messages": len(messages),
            "replies": sum(1 for item in messages if item.get("reference_message_id")),
            "thread_messages": sum(1 for item in messages if item.get("thread_id")),
            "important_messages": sum(1 for item in messages if item["important"]),
            "followup_candidates": sum(1 for item in messages if item["followup"]),
            "channels_active": len(channels),
            "authors_active": len(authors),
            "category_counts": dict(categories.most_common()),
            "top_channels": [{"name": name, "messages": count} for name, count in channels.most_common(10)],
            "top_authors": [{"name": name, "messages": count} for name, count in authors.most_common(10)],
        }

    def build(self, *, hours: int = 24, limit: int = 12) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        duration = timedelta(hours=max(1, min(hours, 24 * 30)))
        current_start = now - duration
        previous_start = current_start - duration

        with self._connect() as db:
            current = self._messages(db, current_start, now)
            previous = self._messages(db, previous_start, current_start)

        current_metrics = self._metrics(current)
        previous_metrics = self._metrics(previous)
        previous_count = previous_metrics["messages"]
        current_count = current_metrics["messages"]
        if previous_count:
            change_pct = round((current_count - previous_count) / previous_count * 100, 2)
        elif current_count:
            change_pct = None
        else:
            change_pct = 0.0

        unresolved = sum(len(event["unresolved_followups"]) for event in self._events(current, 50))
        return {
            "schema_version": 1,
            "generated_at": now.isoformat(),
            "window": {
                "hours": duration.total_seconds() / 3600,
                "current_start": current_start.isoformat(),
                "current_end": now.isoformat(),
                "previous_start": previous_start.isoformat(),
                "previous_end": current_start.isoformat(),
            },
            "health": {
                "status": "attention" if unresolved else "nominal",
                "unresolved_followups": unresolved,
                "activity_change_percent": change_pct,
            },
            "current": current_metrics,
            "previous": previous_metrics,
            "events": self._events(current, limit),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic Discord project intelligence")
    parser.add_argument("--db", default="data/discord.db")
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--output")
    args = parser.parse_args()
    result = DiscordIntelligence(args.db).build(hours=args.hours, limit=args.limit)
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
