"""Version and change primitives shared by glossary and project services."""
from __future__ import annotations
from datetime import datetime

def canonical_hash(value) -> str:
    import hashlib, json
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def compare_month(previous_iso: str, current: datetime) -> bool:
    if not previous_iso:
        return False
    try:
        previous = datetime.fromisoformat(previous_iso.replace("Z", "+00:00"))
    except ValueError:
        return False
    return (previous.year, previous.month) != (current.year, current.month)

def bump_patch(version: str) -> str:
    try:
        major, minor, patch = (int(x) for x in version.split("."))
    except ValueError:
        major, minor, patch = 1, 0, 0
    return f"{major}.{minor}.{patch + 1}"
