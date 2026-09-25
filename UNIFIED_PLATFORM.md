# Unified platform orchestration

All GitHub Actions entry points are consolidated into
`.github/workflows/unified-platform.yml`. The workflow validates the Python
platform, Discord MCP, and Rust code before running scheduled operations.

## Runtime ownership

- `platform/app/orchestrator.py` is the single operational entry point.
- ParaTranz is the authoritative source for project totals and glossary terms.
- Discord is an audit and optional notification transport, never a data store.
- SQLite stores operational history and is archived as a private workflow artifact.
- Public JSON snapshots alone may be committed to Git.
- No translation or review decision is published automatically.

## Schedule

Every six hours, run project synchronization, glossary synchronization,
Discord structure audit, and health diagnostics. The 18:00 UTC run also
generates a daily report; Monday at 18:00 UTC additionally generates a weekly
report. Manual dispatch supports all, daily, weekly, and validation-only modes.

## Failure handling

Each independent job reports its own status. A failed project sync prevents
new reports from being generated using potentially invalid project data;
glossary, audit and health checks continue. A nonzero exit marks the overall
operation as failed after collecting all available diagnostics.

A ParaTranz response with missing or zeroed project totals is rejected rather
than persisted. A previously populated glossary cannot be silently replaced
by an empty API response. Operational JSON is written to
`platform/data/last_run.json`.

## Persistence and recovery

The workflow downloads the most recent available runtime artifact from a
completed unified run, restores `platform.db`, executes the jobs, and uploads
the resulting database and JSON as a 30-day artifact. If there is no prior
artifact, the repository's existing database is the initial seed.

**Limitations:** artifact retention is not permanent storage. Export and
backup to durable external storage before untracking the existing database.
Only aggregate JSON is pushed to the repository. Never commit SQLite journal
files, secrets, raw Discord messages or member identifiers.

## Migration

PR #30 replaces the older scheduled/validation workflows. Do not merge
overlapping PR #28 or #29 without reconciling their changes. Review the
workflow permissions, actual ParaTranz API response format, and GitHub Actions
test results before merging. This rewrite changes the automation control
plane; it does not replace the existing bot commands or the separate Genesis
feature branch.


## Operational API

- `GET /health` is a lightweight liveness check.
- `GET /ready` verifies that the operational SQLite database exists and passes `PRAGMA integrity_check`.
- `GET /api/v1/operations/last` returns the last aggregate orchestration result.
- `GET /api/v1/operations/metrics` returns dashboard-safe counts of successful, failed, and skipped jobs.
- `POST /api/v1/project/sync` is management-only and requires the configured Bearer token.

## Discord history indexing

The Discord indexer keeps a private SQLite history of messages the bot is authorized to see. Gateway events handle create/edit/delete in real time; scheduled REST history sync uses channel cursors to avoid replaying the entire history on every six-hour run. Search, channel reads, server snapshots, channel statistics, and author statistics are exposed through the MCP layer. Discord permissions remain authoritative.

The index is operational/private data and is never committed to Git or exposed through public platform snapshots.
