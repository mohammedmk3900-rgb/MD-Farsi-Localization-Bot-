import asyncio
import os
import unittest

from http_app import SecurityMiddleware


async def _call_app(
    app,
    path="/mcp",
    headers=None,
):
    events = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        events.append(message)

    scope = {
        "type": "http",
        "path": path,
        "method": "POST",
        "headers": [(k.encode(), v.encode()) for k, v in (headers or {}).items()],
    }
    await app(scope, receive, send)
    return events


class SecurityMiddlewareTests(unittest.TestCase):
    def setUp(self):
        async def inner(scope, receive, send):
            await send({"type": "http.response.start", "status": 204, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        self.app = SecurityMiddleware(
            inner,
            auth_required=True,
            auth_token="x" * 40,
            allowed_origins=set(),
        )

    def test_mcp_rejects_missing_token(self):
        events = asyncio.run(_call_app(self.app))
        self.assertEqual(events[0]["status"], 401)

    def test_mcp_rejects_wrong_token(self):
        events = asyncio.run(
            _call_app(self.app, headers={"authorization": "Bearer wrong"})
        )
        self.assertEqual(events[0]["status"], 401)

    def test_mcp_accepts_valid_token_without_origin(self):
        events = asyncio.run(
            _call_app(self.app, headers={"authorization": f"Bearer {'x' * 40}"})
        )
        self.assertEqual(events[0]["status"], 204)

    def test_invalid_origin_is_rejected(self):
        events = asyncio.run(
            _call_app(
                self.app,
                headers={
                    "authorization": f"Bearer {'x' * 40}",
                    "origin": "https://evil.example",
                },
            )
        )
        self.assertEqual(events[0]["status"], 403)

    def test_health_endpoint_is_public(self):
        events = asyncio.run(_call_app(self.app, path="/healthz"))
        self.assertEqual(events[0]["status"], 200)


if __name__ == "__main__":
    unittest.main()
