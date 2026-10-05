# MD News — V11 Genesis

V11 Genesis is the single production application core for Millennium Dawn Farsi Localization.

## Product boundary
- Discord is the only operator interface.
- No web dashboard.
- No standalone management UI.
- ParaTranz is authoritative for translation statistics and the official glossary.
- SQLite is authoritative for Genesis operational state, snapshots and audit history.
- Human reviewers make every final translation/review decision.
- Genesis never automatically publishes translations.

## Architecture
V11 Genesis → Domain → Application Services → Persistence/Integrations → Discord.

The core is transport-neutral: Discord calls application services instead of owning business logic.

## Operational guarantees
- SQLite uses WAL mode, foreign keys and a bounded busy timeout.
- Sync runs receive unique IDs and durable success/failure records.
- Invalid zero-string upstream state is rejected.
- An empty ParaTranz glossary cannot silently erase a previously captured glossary snapshot.
- Audit events are append-only operational history.
- No dashboard frontend, web UI or dashboard dependency exists in V11.

## Human-in-the-loop
Translation intelligence follows: Detect → Explain → Suggest → Human Review.

The system may identify technical or terminology problems, but it does not approve or publish a translation automatically.

## Versioning
V11 progresses through 11.0.0-alpha, 11.0.0-beta, 11.0.0-rc and 11.0.0.

V10 and Platform code remain historical/migration references until the V11 cutover is verified.