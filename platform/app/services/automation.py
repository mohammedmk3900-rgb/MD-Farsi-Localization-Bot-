from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.achievements import AchievementService
from app.services.discord_notifications import DiscordNotificationService


class Automation:
    """Deterministic project operations for the MD Farsi translation team.

    The platform owns the decision logic; Discord is only the delivery surface.
    Every publication is idempotent and persisted in SQLite.
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
        return self.database.get_automation_state(key) != digest

    def _mark_published(self, key: str, value: Any) -> None:
        self.database.set_automation_state(key, self._digest(value), self._now())

    def _embed_if_changed(self, state_key: str, channel: str, title: str, body: str) -> bool:
        value = {"title": title, "body": body}
        if not channel or not self._changed(state_key, value):
            return False
        self.discord.embed(channel, title, body)
        self._mark_published(state_key, value)
        return True

    def _project_state(self) -> tuple[dict[str, Any], dict[str, Any]]:
        rows = self.database.recent_snapshots(2)
        if not rows:
            return {}, {}
        current = rows[0]["payload"].get("project") or {}
        previous = rows[1]["payload"].get("project") if len(rows) > 1 else {}
        return current, previous or {}

    def publish_project(self) -> dict[str, Any]:
        current, previous = self._project_state()
        if not current:
            return {"progress": False, "stats": False, "achievements": 0, "alerts": 0}

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
        if self.settings.channel_progress:
            sent_progress = self._embed_if_changed(
                "publish.progress",
                self.settings.channel_progress,
                "📈 پیشرفت ترجمه • MILLENNIUM DAWN",
                (
                    f"ترجمه: **{progress['translation_percent']:.2f}%**\n"
                    f"بازبینی: **{progress['review_percent']:.2f}%**\n"
                    f"رشته‌های ترجمه‌شده: **{progress['translated']:,} / {progress['strings_total']:,}**\n"
                    f"رشته‌های بازبینی‌شده: **{progress['reviewed']:,}**"
                ),
            )

        if self.settings.channel_stats:
            sent_stats = self._embed_if_changed(
                "publish.stats",
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

        alerts = self._project_quality_alerts(current, previous)
        sent_alerts = self.publish_alerts(alerts)

        payload = {
            "progress": sent_progress,
            "stats": sent_stats,
            "achievements": sent_achievements,
            "alerts": sent_alerts,
        }
        self.application.record("automation.project_published", payload)
        return payload

    def _project_quality_alerts(self, current: dict[str, Any], previous: dict[str, Any]) -> list[str]:
        alerts: list[str] = []
        translation = float(current.get("translation_percent", 0) or 0)
        review = float(current.get("review_percent", 0) or 0)
        if review > translation + 0.01:
            alerts.append("درصد بازبینی از درصد ترجمه بیشتر شده؛ داده‌های منبع یا محاسبه باید بررسی شود.")
        if previous:
            old = float(previous.get("translation_percent", 0) or 0)
            if translation + 0.01 < old:
                alerts.append(f"درصد ترجمه از {old:.2f}% به {translation:.2f}% کاهش یافته؛ احتمال rollback یا تغییر منبع وجود دارد.")
        if int(current.get("translated", 0) or 0) > int(current.get("strings_total", 0) or 0):
            alerts.append("تعداد رشته‌های ترجمه‌شده از کل رشته‌ها بیشتر است؛ snapshot معتبر نیست.")
        return alerts

    def publish_alerts(self, alerts: list[str]) -> int:
        if not alerts or not self.settings.channel_health:
            return 0
        body = "\n".join(f"• {item}" for item in alerts)
        return int(self._embed_if_changed(
            "publish.project_alerts",
            self.settings.channel_health,
            "⚠️ هشدار عملیاتی پروژه • PROJECT ALERTS",
            body,
        ))

    def publish_glossary(self, terms: list[dict[str, Any]]) -> dict[str, Any]:
        if not terms or not self.settings.channel_glossary:
            return {"published": False, "count": len(terms), "qa": {}}

        normalized = sorted(
            [
                {
                    "source": str(item.get("source") or item.get("term") or "").strip(),
                    "target": str(item.get("translation") or item.get("target") or "").strip(),
                    "description": str(item.get("description") or "").strip(),
                }
                for item in terms
            ],
            key=lambda item: (item["source"], item["target"], item["description"]),
        )
        qa = self._glossary_qa(normalized)
        if not self._changed("publish.glossary", normalized):
            return {"published": False, "count": len(terms), "qa": qa}

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

        if qa["issues"] and self.settings.channel_health:
            self._embed_if_changed(
                "publish.glossary_qa",
                self.settings.channel_health,
                "🧪 QA واژه‌نامه • GLOSSARY QUALITY",
                "\n".join(f"• {issue}" for issue in qa["issues"]),
            )

        payload = {"published": True, "count": len(terms), "chunks": len(chunks), "qa": qa}
        self.application.record("automation.glossary_published", payload)
        return payload

    @staticmethod
    def _glossary_qa(terms: list[dict[str, Any]]) -> dict[str, Any]:
        empty = [item["source"] or "(بدون اصطلاح)" for item in terms if not item["source"] or not item["target"]]
        by_source: dict[str, set[str]] = {}
        for item in terms:
            if item["source"]:
                by_source.setdefault(item["source"].casefold(), set()).add(item["target"])
        conflicts = [
            source for source, targets in by_source.items()
            if len(targets) > 1
        ]
        duplicates = len(terms) - len({(x["source"], x["target"], x["description"]) for x in terms})
        issues: list[str] = []
        if empty:
            issues.append(f"{len(empty)} اصطلاح ورودی/ترجمه خالی دارد.")
        if conflicts:
            issues.append(f"{len(conflicts)} اصطلاح برای یک source چند ترجمه متفاوت دارد.")
        if duplicates:
            issues.append(f"{duplicates} ورودی تکراری در واژه‌نامه وجود دارد.")
        return {"issues": issues, "empty_or_incomplete": len(empty), "conflicting_sources": len(conflicts), "duplicates": duplicates}

    def publish_manager_digest(self) -> dict[str, Any]:
        """Publish one concise manager-facing operational digest per state change."""
        current, previous = self._project_state()
        if not current or not self.settings.channel_reports:
            return {"published": False, "reason": "missing_project_or_channel"}

        translated_delta = int(current.get("translated", 0) or 0) - int(previous.get("translated", 0) or 0)
        reviewed_delta = int(current.get("reviewed", 0) or 0) - int(previous.get("reviewed", 0) or 0)
        translation = float(current.get("translation_percent", 0) or 0)
        review = float(current.get("review_percent", 0) or 0)

        intelligence_path = Path(getattr(self.settings, "discord_intelligence_path", "data/discord_intelligence.json"))
        unresolved = 0
        top_categories: list[str] = []
        if intelligence_path.exists():
            try:
                intelligence = json.loads(intelligence_path.read_text(encoding="utf-8"))
                health = intelligence.get("health", {})
                unresolved = int(health.get("unresolved_followups", 0) or 0)
                counts = intelligence.get("current", {}).get("category_counts", {})
                top_categories = [f"{name}: {count}" for name, count in list(counts.items())[:4]]
            except (OSError, ValueError, TypeError):
                pass

        body = (
            f"ترجمه: **{translation:.2f}%** ({translated_delta:+,} رشته)\n"
            f"بازبینی: **{review:.2f}%** ({reviewed_delta:+,} رشته)\n"
            f"پیگیری‌های حل‌نشده: **{unresolved:,}**\n"
            f"موضوعات فعال: **{', '.join(top_categories) if top_categories else '—'}**"
        )
        published = self._embed_if_changed(
            "publish.manager_digest",
            self.settings.channel_reports,
            "🧭 داشبورد مدیر پروژه • MANAGER DIGEST",
            body,
        )
        result = {
            "published": published,
            "translation_percent": translation,
            "review_percent": review,
            "translated_delta": translated_delta,
            "reviewed_delta": reviewed_delta,
            "unresolved_followups": unresolved,
        }
        self.application.record("automation.manager_digest", result)
        return result

    def publish_intelligence(self) -> dict[str, Any]:
        path = Path(getattr(self.settings, "discord_intelligence_path", "data/discord_intelligence.json"))
        if not path.exists():
            return {"published": False, "reason": "artifact_missing"}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"published": False, "reason": "artifact_invalid"}

        current = payload.get("current", {})
        health = payload.get("health", {})
        events = payload.get("events", [])
        body_parts = [
            f"پیام‌ها: **{current.get('messages', 0):,}**",
            f"پاسخ‌ها: **{current.get('replies', 0):,}**",
            f"اعضای فعال: **{current.get('authors_active', 0):,}**",
            f"کانال‌های فعال: **{current.get('channels_active', 0):,}**",
            f"تغییر فعالیت: **{health.get('activity_change_percent') if health.get('activity_change_percent') is not None else '—'}%**",
            f"پیگیری‌های حل‌نشده: **{health.get('unresolved_followups', 0):,}**",
        ]
        for event in events[:5]:
            body_parts.append(f"• [{event.get('category', 'عمومی')}] {event.get('message_count', 0)} پیام، {event.get('participant_count', 0)} مشارکت‌کننده")

        published = self._embed_if_changed(
            "publish.intelligence",
            self.settings.channel_reports,
            "🧠 وضعیت عملیاتی جامعه ترجمه • PROJECT INTELLIGENCE",
            "\n".join(body_parts),
        )
        result = {"published": published, "events": len(events), "unresolved_followups": health.get("unresolved_followups", 0)}
        self.application.record("automation.intelligence_published", result)
        return result
