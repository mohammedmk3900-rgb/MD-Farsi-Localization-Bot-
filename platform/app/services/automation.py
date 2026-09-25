from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.services.achievements import AchievementService
from app.services.discord_notifications import DiscordNotificationService


class Automation:
    """Deterministic Discord publishing for project state.

    Nothing is published unless its source state changed. Glossary and
    milestone state is persisted in SQLite so scheduled runs stay idempotent.
    """

    def __init__(self, application):
        self.application = application
        self.settings = application.context.settings
        self.database = application.context.database
        self.discord = DiscordNotificationService(self.settings)
        self.achievements = AchievementService()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _digest(self, value: Any) -> str:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _changed(self, key: str, value: Any) -> bool:
        digest = self._digest(value)
        if self.database.get_automation_state(key) == digest:
            return False
        self.database.set_automation_state(key, digest, self._now())
        return True

    def publish_project(self) -> dict[str, Any]:
        rows = self.database.recent_snapshots(2)
        if not rows:
            return {"progress": False, "stats": False, "achievements": 0}

        current = rows[0]["payload"].get("project") or {}
        previous = rows[1]["payload"].get("project") if len(rows) > 1 else {}

        progress = {
            "translation_percent": round(float(current.get("translation_percent", 0) or 0), 2),
            "review_percent": round(float(current.get("review_percent", 0) or 0), 2),
            "translated": int(current.get("translated", 0) or 0),
            "reviewed": int(current.get("reviewed", 0) or 0),
            "strings_total": int(current.get("strings_total", 0) or 0),
        }
        stats = {
            "words_total": int(current.get("words_total", 0) or 0),
            "strings_total": progress["strings_total"],
            "files": int(current.get("files", 0) or 0),
            "members": int(current.get("members", 0) or 0),
            "translated": progress["translated"],
            "reviewed": progress["reviewed"],
        }

        sent_progress = False
        sent_stats = False
        if self.settings.channel_progress and self._changed("publish.progress", progress):
            self.discord.embed(
                self.settings.channel_progress,
                "📈 پیشرفت ترجمه • MILLENNIUM DAWN",
                (
                    f"ترجمه: **{progress['translation_percent']:.2f}%**\n"
                    f"بازبینی: **{progress['review_percent']:.2f}%**\n"
                    f"رشته‌های ترجمه‌شده: **{progress['translated']:,} / {progress['strings_total']:,}**\n"
                    f"رشته‌های بازبینی‌شده: **{progress['reviewed']:,}**"
                ),
            )
            sent_progress = True

        if self.settings.channel_stats and self._changed("publish.stats", stats):
            self.discord.embed(
                self.settings.channel_stats,
                "📊 آمار پروژه • PROJECT STATS",
                (
                    f"کلمات: **{stats['words_total']:,}**\n"
                    f"رشته‌ها: **{stats['strings_total']:,}**\n"
                    f"فایل‌ها: **{stats['files']:,}**\n"
                    f"اعضا: **{stats['members']:,}**\n"
                    f"ترجمه‌شده: **{stats['translated']:,}**\n"
                    f"بازبینی‌شده: **{stats['reviewed']:,}**"
                ),
            )
            sent_stats = True

        previous_percent = float(previous.get("translation_percent", 0) or 0)
        current_percent = float(current.get("translation_percent", 0) or 0)
        sent_achievements = 0
        for achievement in self.achievements.crossed(previous_percent, current_percent):
            key = f"publish.achievement.{achievement['percent']}"
            if self.database.get_automation_state(key) or not self.settings.channel_achievements:
                continue
            self.discord.embed(
                self.settings.channel_achievements,
                f"{achievement['icon']} {achievement['title']}",
                achievement["description"],
            )
            self.database.set_automation_state(key, "published", self._now())
            sent_achievements += 1

        payload = {
            "progress": sent_progress,
            "stats": sent_stats,
            "achievements": sent_achievements,
        }
        self.application.record("automation.project_published", payload)
        return payload

    def publish_glossary(self, terms: list[dict[str, Any]]) -> dict[str, Any]:
        if not terms or not self.settings.channel_glossary:
            return {"published": False, "count": len(terms)}

        normalized = sorted(
            [
                {
                    "source": item.get("source") or item.get("term") or "",
                    "target": item.get("translation") or item.get("target") or "",
                    "description": item.get("description") or "",
                }
                for item in terms
            ],
            key=lambda item: (item["source"], item["target"]),
        )
        if not self._changed("publish.glossary", normalized):
            return {"published": False, "count": len(terms)}

        chunks: list[str] = []
        current: list[str] = []
        size = 0
        for item in normalized:
            line = f"• **{item['source']}** → {item['target']}"
            if item["description"]:
                line += f" — {item['description']}"
            if current and size + len(line) + 1 > 3800:
                chunks.append("\n".join(current))
                current, size = [], 0
            current.append(line)
            size += len(line) + 1
        if current:
            chunks.append("\n".join(current))

        for index, chunk in enumerate(chunks, 1):
            self.discord.embed(
                self.settings.channel_glossary,
                f"📚 واژه‌نامه رسمی • بخش {index}/{len(chunks)}",
                chunk,
            )

        payload = {"published": True, "count": len(terms), "chunks": len(chunks)}
        self.application.record("automation.glossary_published", payload)
        return payload
