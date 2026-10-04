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

## Autonomous Operations Scheduler

The platform includes a persistent scheduler for recurring project operations. It is separate from GitHub Actions so automation remains an application concern.

Run one due cycle:
```bash
cd platform
python run_scheduler.py --once
```

Run continuously:
```bash
cd platform
python run_scheduler.py
```

Default cadence:
- health: every 30 minutes
- sync: every 6 hours
- glossary: every 6 hours
- Discord audit: every 12 hours
- manager read model: every hour
- daily report: every 24 hours
- weekly report: every 7 days

Scheduler state is persisted in SQLite. Each job uses an atomic execution lease, so two scheduler processes cannot execute the same job concurrently. Failed jobs are retried after a short backoff and crashed jobs become claimable after the lease expires.

Environment controls:
- `SCHEDULER_POLL_SECONDS`: scheduler polling interval, default 30
- `SCHEDULER_LEASE_SECONDS`: execution lease, default 900
- `LOG_LEVEL`: logging level, default INFO

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


## Unified runtime

For a normal deployment, start the application with:

```bash
cd platform
python run_api.py
```

This launcher enables the embedded autonomous scheduler, so FastAPI and the persistent scheduler share the same application context and SQLite state. The scheduler can still be run independently with `python run_scheduler.py` for worker-style deployments.

The recurring business scheduler is owned by the application. GitHub Actions is validation/manual maintenance infrastructure, not the production business scheduler.
