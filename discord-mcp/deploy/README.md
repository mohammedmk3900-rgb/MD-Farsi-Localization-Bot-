# Production deployment

This deployment publishes the Discord MCP server at:

`https://<MCP_DOMAIN>/mcp`

The MCP SDK's Streamable HTTP transport already exposes the MCP endpoint at `/mcp`. The local Uvicorn process is protected by a bearer token and optional Origin allowlist; Caddy terminates HTTPS and forwards only to the internal container.

## 1. Prepare configuration

Copy `production.env.example` to `production.env` and set:

- `MCP_DOMAIN` to a DNS name pointing to the host.
- `DISCORD_BOT_TOKEN` and `DISCORD_GUILD_ID`.
- `MCP_AUTH_TOKEN` to a random secret with at least 32 characters.

Do not commit `production.env`.

## 2. Discord bot permissions

The bot must be able to view the channels and threads you want indexed. Enable the Discord **Message Content Intent** so message bodies are available. Do not grant Administrator unless the server actually needs it.

## 3. Start

```bash
docker compose --env-file production.env up -d --build
```

Caddy will request and renew the HTTPS certificate automatically when the hostname is publicly reachable.

## 4. Verify

```bash
docker compose --env-file production.env ps
curl -fsS https://${MCP_DOMAIN}/healthz
```

The MCP endpoint is:

`https://${MCP_DOMAIN}/mcp`

For a local protocol check, use MCP Inspector against the same Streamable HTTP endpoint. The production endpoint must remain protected; do not expose the container port directly to the internet.

## 5. ChatGPT

Add the HTTPS `/mcp` endpoint from the ChatGPT MCP/App connection flow. Use the authentication option supported by the ChatGPT connection UI and keep the server-side bearer token secret. If the ChatGPT flow requires OAuth rather than a static bearer token, place an OAuth-capable proxy in front of this service rather than removing authentication.

## Operations

- SQLite lives in the named Docker volume `discord_mcp_data`.
- `DISCORD_BACKFILL_ON_START=false` avoids a full history scan on every container restart. Use the MCP `deep_scan_server` or scheduled indexing instead.
- Logs are emitted to stdout/stderr for Docker.
- Health checks are unauthenticated and reveal only a small status string.
