# Discord Indexer & MCP

This service provides a permission-respecting read model of the configured Discord guild.

## Data flow

1. The Gateway bot receives authorized guild events.
2. On startup it backfills accessible text, forum and thread history.
3. Message create/edit/delete events keep SQLite current.
4. The MCP server exposes structure, indexed history, search and aggregate analytics.

## MCP tools

- `get_server_overview`
- `get_server_snapshot(include_messages, message_limit_per_channel)`
- `full_server_audit(include_messages, message_limit_per_channel)` — broad read-only guild audit including members, permissions, threads, resources, moderation state and indexed activity
- `list_channels`
- `list_roles`
- `sync_channel_history`
- `sync_server_history`
- `get_sync_status`
- `search_index`
- `read_channel`
- `get_channel_statistics`
- `get_author_statistics`

The bot never bypasses Discord permissions. Private channels unavailable to the bot are not indexed. The full audit is read-only and uses only endpoints the bot can access; unavailable optional resources are reported as empty rather than fabricated. Deleted messages are represented as local tombstones and their content is removed from the index.

The Discord `message_content` privileged intent must be enabled for message content to be available. Historical backfill is limited to channels/history the bot can actually read.

The SQLite database contains message content and must be treated as private operational data. It must not be committed to Git or exposed in public snapshots.


## Full server access model

The MCP exposes a read-only, permission-respecting view of the configured Discord guild.

### Snapshot and audit tools

- `get_server_overview` — lightweight guild metadata and indexed counts.
- `get_server_snapshot(full=true)` — complete snapshot mode.
- `full_server_audit` — broad audit covering guild settings, categories, channels, permission overwrites, roles, members, active threads, emojis, stickers, scheduled events, bans, integrations, AutoMod rules, invites, redacted webhooks, stage instances, audit-log entries, and indexed activity.
- `deep_scan_server` — performs an authorized history scan and returns scan/index status.

### History access

- `search_messages` — query indexed history with channel, author, and timestamp filters.
- `get_message` — fetch one indexed message.
- `read_channel` / `read_thread` / `read_replies` — read indexed history.
- `read_channel_page` — read live channel history with Discord pagination cursors.
- `get_index_cursors` — inspect per-channel sync completeness.

The indexer stores message relationships, thread IDs, attachment/link counts, edits, and deletion state. Gateway backfill uses Discord's native rate-limit handling; REST access retries 429 responses with the server-provided retry delay.

The system never bypasses Discord permissions. Private or otherwise inaccessible resources are reported as unavailable/empty rather than fabricated. Webhook tokens and integration account objects are never exposed through the MCP.

A single response is intentionally not treated as the entire historical dataset: large servers require indexed search and pagination. This keeps the MCP usable while still making the complete authorized history queryable.
