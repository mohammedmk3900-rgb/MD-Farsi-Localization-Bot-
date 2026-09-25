from __future__ import annotations


ROLE_PERMISSIONS = {
    "owner": {"*"},
    "project_manager": {"tasks.manage", "report.read", "health.read", "sync.run"},
    "review_manager": {"tasks.review", "translation.review", "glossary.read"},
    "reviewer": {"tasks.review", "translation.review", "glossary.read"},
    "translator": {"tasks.self", "translation.check", "glossary.read"},
    "contributor": {"tasks.self", "glossary.read"},
}


def role_permissions(role: str) -> set[str]:
    return ROLE_PERMISSIONS.get(role, set())


def allowed(role: str, permission: str) -> bool:
    permissions = role_permissions(role)
    return "*" in permissions or permission in permissions
