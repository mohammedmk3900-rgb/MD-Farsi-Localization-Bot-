# MD Farsi Localization Platform — Next

A clean-room rewrite of the Millennium Dawn Farsi Localization automation platform.

## Principles
- ParaTranz is the translation and glossary source of truth.
- Discord is an operational interface, not a database.
- Human review/approval remains human-controlled.
- Automation owns collection, synchronization, analytics, reporting, health checks and recovery.
- Public snapshots contain aggregates only; never commit tokens, message content or member PII.
- One canonical domain model feeds API, Discord and dashboard.

## Runtime
- Python 3.12
- FastAPI + Uvicorn
- SQLite with an event-oriented persistence layer
- discord.py
- httpx
- pytest

## Layout
```
platform/
  app/
    domain/          # canonical models and policies
    integrations/    # Discord / ParaTranz adapters
    services/        # orchestration and automation
    api/             # HTTP API
    bot/             # Discord application
    persistence/     # SQLite repositories
  tests/
  pyproject.toml
```

This directory is the replacement runtime. Existing V9/V8 components remain untouched until migration validation is complete.
