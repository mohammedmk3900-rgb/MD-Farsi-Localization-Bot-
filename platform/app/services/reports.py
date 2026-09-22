from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class ReportService:
    def build(self, snapshot: dict[str, Any], period: str = "daily") -> dict[str, Any]:
        project = snapshot.get("project", {})
        return {
            "period": period,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "title": f"گزارش {period} پروژه فارسی‌سازی Millennium Dawn",
            "project": project,
        }
