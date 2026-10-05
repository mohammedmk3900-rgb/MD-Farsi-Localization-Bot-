from __future__ import annotations

from app.services.translation import TranslationService


def test_translation_check_detects_missing_tokens():
    check = TranslationService().check("Hello $NAME$ §RISK", "سلام")
    kinds = {finding["kind"] for finding in check.findings}
    assert "missing_token" in kinds
    assert check.publish_allowed is False


def test_translation_check_accepts_preserved_tokens():
    check = TranslationService().check("Hello $NAME$ §RISK", "سلام $NAME$ §RISK")
    assert check.findings == []
    assert check.approved_for_review is True
    assert check.publish_allowed is False
