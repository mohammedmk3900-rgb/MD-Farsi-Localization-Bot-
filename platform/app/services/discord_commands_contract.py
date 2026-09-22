from __future__ import annotations

COMMANDS = (
    "stats",
    "progress",
    "glossary",
    "history",
    "health",
    "achievements",
    "sync",
    "report",
)


def contract() -> list[dict[str, str]]:
    return [{"name": name, "path": f"/project {name}"} for name in COMMANDS]
