from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class ProjectManagerService:
    """Builds an aggregate, manager-facing read model from durable project state.

    It deliberately contains no raw Discord content, identities, tokens, or
    private message bodies. It answers operational questions: where are we,
    what changed, what is the review gap, and where should attention go?
    """

    def __init__(self, database):
        self.database = database

    @staticmethod
    def _project(row: dict[str, Any] | None) -> dict[str, Any]:
        return (row or {}).get("payload", {}).get("project") or {}

    def build(self) -> dict[str, Any]:
        rows = self.database.recent_snapshots(8)
        current = self._project(rows[0] if rows else None)
        previous = self._project(rows[1] if len(rows) > 1 else None)

        translated = int(current.get("translated", 0) or 0)
        reviewed = int(current.get("reviewed", 0) or 0)
        strings = int(current.get("strings_total", 0) or 0)
        translation_pct = float(current.get("translation_percent", 0) or 0)
        review_pct = float(current.get("review_percent", 0) or 0)

        translated_delta = translated - int(previous.get("translated", 0) or 0)
        reviewed_delta = reviewed - int(previous.get("reviewed", 0) or 0)
        review_gap = max(0, translated - reviewed)

        recent_velocity: list[dict[str, Any]] = []
        for newer, older in zip(rows, rows[1:]):
            new_p = self._project(newer)
            old_p = self._project(older)
            recent_velocity.append({
                "translated_delta": int(new_p.get("translated", 0) or 0) - int(old_p.get("translated", 0) or 0),
                "reviewed_delta": int(new_p.get("reviewed", 0) or 0) - int(old_p.get("reviewed", 0) or 0),
            })

        positive_translation = [x["translated_delta"] for x in recent_velocity if x["translated_delta"] > 0]
        positive_review = [x["reviewed_delta"] for x in recent_velocity if x["reviewed_delta"] > 0]
        avg_translation_velocity = round(sum(positive_translation) / len(positive_translation), 2) if positive_translation else 0.0
        avg_review_velocity = round(sum(positive_review) / len(positive_review), 2) if positive_review else 0.0

        attention: list[str] = []
        if review_gap:
            attention.append("صف بازبینی از ترجمه عقب است.")
        if translation_pct > 0 and review_pct / translation_pct < 0.25:
            attention.append("نسبت پوشش بازبینی نسبت به ترجمه پایین است.")
        if translated_delta == 0:
            attention.append("در آخرین snapshot پیشرفت ترجمه‌ای ثبت نشده است.")
        if reviewed_delta == 0 and translated:
            attention.append("در آخرین snapshot پیشرفت بازبینی ثبت نشده است.")
        if strings and translated > strings:
            attention.append("داده پروژه ناسازگار است: translated از strings_total بیشتر است.")

        next_milestone = next((level for level in (1, 10, 25, 50, 75, 100) if translation_pct < level), 100)

        return {
            "schema_version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "project_id": current.get("project_id"),
            "status": "attention" if attention else "on_track",
            "progress": {
                "translation_percent": round(translation_pct, 2),
                "review_percent": round(review_pct, 2),
                "translated": translated,
                "reviewed": reviewed,
                "strings_total": strings,
                "review_gap": review_gap,
                "next_milestone_percent": next_milestone,
            },
            "delta": {
                "translated": translated_delta,
                "reviewed": reviewed_delta,
            },
            "velocity": {
                "average_translation_per_snapshot": avg_translation_velocity,
                "average_review_per_snapshot": avg_review_velocity,
                "samples": len(recent_velocity),
            },
            "attention": attention,
        }
