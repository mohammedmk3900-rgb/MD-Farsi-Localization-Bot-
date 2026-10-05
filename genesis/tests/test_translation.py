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


def test_translation_check_detects_empty_translation_and_format_drift():
    check = TranslationService().check("Line 1\nLine 2", "")
    kinds = {finding["kind"] for finding in check.findings}
    assert "empty_translation" in kinds
    assert "newline_mismatch" in kinds


def test_translation_check_detects_duplicate_token():
    check = TranslationService().check("$NAME$", "$NAME$ $NAME$")
    finding = next(f for f in check.findings if f["kind"] == "unexpected_token")
    assert finding["tokens"] == ["$NAME$"]
