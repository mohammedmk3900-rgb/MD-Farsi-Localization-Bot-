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
    "center",
    "tasks",
    "task_create",
    "task_claim",
    "task_submit",
    "task_complete",
    "check",
)


def contract() -> list[dict[str, str]]:
    return [{"name": name, "path": f"/project {name}"} for name in COMMANDS]
