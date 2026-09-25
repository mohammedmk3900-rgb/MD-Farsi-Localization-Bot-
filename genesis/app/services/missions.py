from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import Priority


@dataclass(frozen=True)
class Mission:
    title: str
    scope: str
    priority: Priority = Priority.NORMAL
    reward: int = 0


class MissionService:
    def generate(self, scopes: list[str], limit: int = 5) -> list[Mission]:
        if limit < 1:
            return []
        return [
            Mission(
                title=f"ترجمه و بررسی {scope}",
                scope=scope,
                priority=Priority.NORMAL,
                reward=10,
            )
            for scope in scopes[:limit]
        ]
