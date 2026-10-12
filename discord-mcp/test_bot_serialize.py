"""Regression tests for Gateway message normalization."""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

_TEST_ROOT = tempfile.TemporaryDirectory(prefix="dawnnexus-bot-tests-")
os.environ.setdefault("DISCORD_BOT_TOKEN", "test-token")
os.environ.setdefault("DISCORD_GUILD_ID", "1")
os.environ["DISCORD_DB_PATH"] = str(Path(_TEST_ROOT.name) / "discord.db")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from bot import serialize


def test_gateway_serialization_preserves_reply_and_content_metadata() -> None:
    channel = SimpleNamespace(id=10, name="translation")
    author = SimpleNamespace(id=20, global_name="Reviewer", name="reviewer")
    reference = SimpleNamespace(message_id=100, channel_id=10)
    message = SimpleNamespace(
        id=101,
        channel=channel,
        author=author,
        content="Approved https://example.com",
        created_at=datetime(2026, 10, 11, tzinfo=timezone.utc),
        edited_at=None,
        jump_url="https://discord.com/channels/1/10/101",
        reference=reference,
        attachments=[object()],
        type=0,
    )

    result = serialize(message)

    assert result["reference_message_id"] == "100"
    assert result["reference_channel_id"] == "10"
    assert result["thread_id"] is None
    assert result["message_type"] == 0
    assert result["attachment_count"] == 1
    assert result["link_count"] == 1
    assert result["url"] == message.jump_url
