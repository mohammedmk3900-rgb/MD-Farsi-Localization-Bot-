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

## ParaTranz API client

The read-only ParaTranz adapter uses the documented `Authorization` header format (the raw API token, without a `Bearer ` prefix). A pasted Bearer-prefixed value is normalized before sending. Keep `PARATRANZ_TOKEN` in the deployment secret store and never log it.

The project snapshot is built from `GET /projects/{projectId}`, `GET /projects/{projectId}/files`, and—when the project response does not contain a member count—`GET /projects/{projectId}/members`. Translation counters are aggregated from each file's documented `total`, `translated`, `reviewed`, and `words` fields; the client does not assume undocumented aggregate fields exist on the project object.

Transport settings:
- `PARATRANZ_BASE_URL`: API base URL, default `https://paratranz.cn/api`
- `PARATRANZ_TIMEOUT_SECONDS`: request timeout, default 20 seconds
- `PARATRANZ_MAX_RETRIES`: bounded retries for rate limits and transient upstream failures, default 3
- `PARATRANZ_PAGE_SIZE`: glossary/member page size, default 100
- `PARATRANZ_MAX_PAGES`: pagination safety limit, default 100

Successful responses with an unknown or incomplete shape are treated as errors, not empty collections. Empty/inconsistent project snapshots are rejected to prevent a broken upstream response from overwriting known-good project state. Glossary sync also de-duplicates repeated pages and protects a previously populated glossary from an empty response.


### Expanded read-only API surface

The adapter exposes typed read helpers for project metadata, project discovery, file metadata and translations, members, strings, terms and term history, scores, project history, file revisions, issues, artifacts and the latest artifact. Collection helpers support bounded pagination, query filters, response-shape validation and duplicate-page detection. The write/mutation endpoints (translation edits, file uploads, term imports/deletes and project changes) are intentionally not exposed to scheduled automation; translation decisions remain human-approved.

The `PARATRANZ_PAGE_SIZE` and `PARATRANZ_MAX_PAGES` settings are wired into the glossary/member pagination paths. Requests use the raw ParaTranz API token in `Authorization`, never follow redirects with credentials, reject unsafe relative paths, use bounded retries for safe GET requests, and avoid logging credentials.

Reference: [ParaTranz OpenAPI endpoint catalog](https://github.com/Gebardensprache/paratranz-rs#documentation-for-api-endpoints).
