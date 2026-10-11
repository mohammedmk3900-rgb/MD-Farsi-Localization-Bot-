# Discord Indexer & MCP

This service provides a permission-respecting read model of the configured Discord guild.

## Data flow

1. The Gateway bot receives authorized guild events.
2. On startup it backfills accessible text channels and cached active threads.
3. Message create/edit/delete events keep SQLite current, including reply references, thread IDs, attachment counts, and link counts.
4. The MCP server can discover active threads and best-effort archived threads through Discord REST endpoints.
5. `deep_scan_server` combines history synchronization with a server snapshot; `full_server_audit` returns the broadest read-only audit currently available to the bot.

## MCP tools

- `get_server_overview`
- `get_server_snapshot(include_messages, message_limit_per_channel)`
- `list_channels`
- `list_roles`
- `sync_channel_history`
- `sync_server_history`
- `get_sync_status`
- `search_index`
- `read_channel`
- `get_channel_statistics`
- `get_author_statistics`
- `read_thread`, `read_replies`, `read_channel_page`, `get_message`, `search_messages`
- `deep_scan_server`, `full_server_audit`, `get_server_snapshot(full=true)`
- `get_index_cursors`, `get_project_intelligence`, `get_news_digest`

For a first comprehensive pass, call `deep_scan_server` and inspect its per-channel results and `complete` flags. A limited scan (`max_pages_per_channel > 0`) is intentionally partial. Re-run it until historical backfill is complete, and use `get_index_cursors` to see per-channel progress.

The bot never bypasses Discord permissions. Private channels unavailable to the bot are not indexed. Deleted messages are represented as local tombstones and their content is removed from the index.

The Discord `message_content` privileged intent must be enabled for message content to be available. Historical backfill is limited to channels/history the bot can actually read.

The SQLite database contains message content and must be treated as private operational data. It must not be committed to Git or exposed in public snapshots.
