from __future__ import annotations

LEGACY_WEBHOOK_ENV = {
    "DISCORD_WEBHOOK_URL",
    "DISCORD_PROGRESS_WEBHOOK_URL",
    "DISCORD_ACHIEVEMENTS_WEBHOOK_URL",
    "DISCORD_HEALTH_WEBHOOK_URL",
    "DISCORD_REPORTS_WEBHOOK_URL",
    "DISCORD_GLOSSARY_WEBHOOK_URL",
}


def migration_contract() -> dict:
    return {
        "legacy_transport": "webhook",
        "replacement": "MD news Bot API",
        "legacy_env_to_remove": sorted(LEGACY_WEBHOOK_ENV),
        "migration_policy": "dual-read, single-write, then remove",
    }
