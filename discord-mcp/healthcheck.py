"""Container health check for the Discord MCP HTTP listener."""
from __future__ import annotations

import os
import socket
import sys


def main() -> int:
    host = os.getenv("MCP_HEALTH_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", "8000"))
    try:
        with socket.create_connection((host, port), timeout=2):
            return 0
    except OSError as exc:
        print(f"healthcheck failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
