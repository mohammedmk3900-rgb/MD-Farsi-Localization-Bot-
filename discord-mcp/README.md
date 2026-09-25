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
- `list_channels`
- `list_roles`
- `sync_channel_history`
- `sync_server_history`
- `get_sync_status`
- `search_index`
- `read_channel`
- `get_channel_statistics`
- `get_author_statistics`

The bot never bypasses Discord permissions. Private channels unavailable to the bot are not indexed. Deleted messages are represented as local tombstones and their content is removed from the index.

The Discord `message_content` privileged intent must be enabled for message content to be available. Historical backfill is limited to channels/history the bot can actually read.

The SQLite database contains message content and must be treated as private operational data. It must not be committed to Git or exposed in public snapshots.
