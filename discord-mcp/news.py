"""Deterministic Discord project-news engine.

Turns indexed Discord history into a compact, safe project-news digest without
modifying messages or attempting to infer private information.
"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

CATEGORIES: dict[str, tuple[str, ...]] = {
    "ترجمه": ("ترجمه", "translate", "translation", "localization", "ترجمه‌", "translated"),
    "بازبینی": ("بازبینی", "review", "reviewed", "اصلاح", "غلط", "بررسی"),
    "واژه‌نامه": ("واژه", "glossary", "اصطلاح", "ترمینولوژی", "term"),
    "پروژه": ("پروژه", "project", "آپدیت", "update", "نسخه", "release", "ربات", "bot"),
    "همکاری": ("همکاری", "عضو", "member", "مترجم", "translator", "همکار"),
    "مشکل": ("خطا", "error", "bug", "مشکل", "خراب", "fail", "failed", "ارور"),
}

IMPORTANT_MARKERS = (
    "urgent", "مهم", "فوری", "خطا", "error", "bug", "failed", "خراب",
    "announcement", "اعلام", "release", "نسخه", "update", "آپدیت",
)

def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None

def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\u200c", " ")).strip()

def _category(content: str) -> str:
    lowered = content.casefold()
    scores = {
        name: sum(1 for word in words if word.casefold() in lowered)
        for name, words in CATEGORIES.items()
    }
    best = max(scores, key=scores.get)
    return best if scores[best] else "عمومی"

def _important(content: str) -> bool:
    lowered = content.casefold()
    return any(marker.casefold() in lowered for marker in IMPORTANT_MARKERS)

class DiscordNewsEngine:
    def __init__(self, db_path: str | Path) -> None:
        self.path = str(db_path)

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        return db

    def _init(self, db: sqlite3.Connection) -> None:
        db.execute("""
            CREATE TABLE IF NOT EXISTS news_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

    def digest(
        self,
        *,
        hours: int = 24,
        limit: int = 12,
        mark_read: bool = False,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=max(1, min(hours, 24 * 30)))

        with self._connect() as db:
            self._init(db)
            row = db.execute(
                "SELECT value FROM news_state WHERE key='last_digest_at'"
            ).fetchone()
            stored_cutoff = _parse_time(row["value"]) if row else None
            effective_cutoff = max(
                cutoff,
                stored_cutoff or cutoff,
            )
            rows = db.execute("""
                SELECT id, channel_id, channel_name, author_id, author_name,
                       content, timestamp, edited_timestamp, url
                FROM messages
                WHERE deleted=0 AND timestamp IS NOT NULL
                ORDER BY timestamp DESC
            """).fetchall()

            messages: list[dict[str, Any]] = []
            for row in rows:
                timestamp = _parse_time(row["timestamp"])
                if timestamp is None or timestamp < effective_cutoff or timestamp > now:
                    continue
                content = _normalize(row["content"] or "")
                if not content:
                    continue
                item = dict(row)
                item["content"] = content
                item["category"] = _category(content)
                item["important"] = _important(content)
                messages.append(item)
                if len(messages) >= max(1, min(limit * 8, 200)):
                    break

            by_category: dict[str, int] = {}
            for item in messages:
                by_category[item["category"]] = by_category.get(item["category"], 0) + 1

            highlights = [
                {
                    "id": item["id"],
                    "channel": item["channel_name"],
                    "author": item["author_name"],
                    "content": item["content"][:500],
                    "timestamp": item["timestamp"],
                    "category": item["category"],
                    "important": item["important"],
                    "url": item["url"],
                }
                for item in messages
                if item["important"]
            ][:limit]

            if len(highlights) < limit:
                seen = {item["id"] for item in highlights}
                for item in messages:
                    if item["id"] in seen:
                        continue
                    highlights.append({
                        "id": item["id"],
                        "channel": item["channel_name"],
                        "author": item["author_name"],
                        "content": item["content"][:500],
                        "timestamp": item["timestamp"],
                        "category": item["category"],
                        "important": item["important"],
                        "url": item["url"],
                    })
                    if len(highlights) >= limit:
                        break

            result = {
                "schema_version": 1,
                "generated_at": now.isoformat(),
                "since": effective_cutoff.isoformat(),
                "until": now.isoformat(),
                "message_count": len(messages),
                "category_counts": dict(sorted(by_category.items(), key=lambda pair: (-pair[1], pair[0]))),
                "active_channels": len({item["channel_id"] for item in messages}),
                "active_authors": len({item["author_id"] for item in messages if item["author_id"]}),
                "highlights": highlights,
            }

            if mark_read:
                db.execute(
                    """INSERT INTO news_state(key,value) VALUES('last_digest_at,?)""",
                    (now.isoformat(),),
                )
                db.execute(
                    """INSERT INTO news_state(key,value) VALUES('last_digest_at',?)
                    ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
                    (now.isoformat(),),
                )
                db.commit()

            return result

def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/discord.db")
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--output")
    parser.add_argument("--mark-read", action="store_true")
    args = parser.parse_args()
    result = DiscordNewsEngine(args.db).digest(
        hours=args.hours,
        limit=args.limit,
        mark_read=args.mark_read,
    )
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
