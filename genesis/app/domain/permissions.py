from __future__ import annotations

ROLES: dict[str, frozenset[str]] = {
    "owner": frozenset({"*"}),
    "project_manager": frozenset({
        "project.read", "tasks.manage", "reports.read", "health.read", "sync.run"
    }),
    "review_manager": frozenset({
        "project.read", "tasks.review", "translation.review", "glossary.read", "reports.read"
    }),
    "reviewer": frozenset({
        "project.read", "tasks.review", "translation.review", "glossary.read"
    }),
    "translator": frozenset({
        "project.read", "tasks.self", "translation.check", "glossary.read"
    }),
    "contributor": frozenset({
        "project.read", "tasks.self", "glossary.read"
    }),
}


def allowed(role: str, permission: str) -> bool:
    permissions = ROLES.get(role, frozenset())
    return "*" in permissions or permission in permissions
