"""Read-only JSON API for persisted Command Center state."""
from __future__ import annotations
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

STATE = Path("data/command_center.json")

class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: object) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path != "/api/v1/command-center":
            self._send(404, {"error": "not_found"})
            return
        if not STATE.exists():
            self._send(503, {"error": "state_unavailable"})
            return
        try:
            self._send(200, json.loads(STATE.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            self._send(500, {"error": "invalid_state"})

    def log_message(self, *_args) -> None:
        return

def serve(host: str = "127.0.0.1", port: int = 8787) -> None:
    ThreadingHTTPServer((host, port), Handler).serve_forever()

if __name__ == "__main__":
    serve()
