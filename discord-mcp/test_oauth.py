"""Security regression tests for the built-in DawnNexus OAuth provider."""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from oauth import DawnNexusOAuthProvider


def test_login_attempts_are_limited_and_reset_after_window(tmp_path: Path) -> None:
    provider = DawnNexusOAuthProvider(str(tmp_path / "oauth.db"), "https://example.test")

    assert provider.login_attempts_remaining("192.0.2.10") == 5
    assert [provider.record_login_failure("192.0.2.10") for _ in range(5)] == [4, 3, 2, 1, 0]
    assert provider.login_attempts_remaining("192.0.2.10") == 0

    provider.clear_login_failures("192.0.2.10")
    assert provider.login_attempts_remaining("192.0.2.10") == 5


def test_login_attempt_limits_are_isolated_per_ip(tmp_path: Path) -> None:
    provider = DawnNexusOAuthProvider(str(tmp_path / "oauth.db"), "https://example.test")

    for _ in range(5):
        provider.record_login_failure("192.0.2.11")

    assert provider.login_attempts_remaining("192.0.2.11") == 0
    assert provider.login_attempts_remaining("192.0.2.12") == 5
