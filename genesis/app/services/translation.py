from __future__ import annotations

import re
from uuid import uuid4
from datetime import datetime, timezone

from collections import Counter

from app.domain.models import GlossaryTerm, TranslationCheck

TOKEN_PATTERNS = (
    re.compile(r"\$[^\s$]+"),
    re.compile(r"\[[^\]]+\]"),
    re.compile(r"§[A-Za-z0-9_]+"),
    re.compile(r"£[A-Za-z0-9_]+"),
)


def tokens(text: str) -> set[str]:
    return {token for pattern in TOKEN_PATTERNS for token in pattern.findall(text)}


def token_counts(text: str) -> Counter[str]:
    return Counter(token for pattern in TOKEN_PATTERNS for token in pattern.findall(text))


class TranslationService:
    """Deterministic translation QA. Detects, explains and suggests; never publishes."""

    def check(
        self,
        source: str,
        translation: str,
        glossary: list[GlossaryTerm] | None = None,
    ) -> TranslationCheck:
        findings: list[dict] = []

        if not source.strip():
            findings.append({
                "kind": "empty_source",
                "severity": "error",
                "message": "متن مبدأ خالی است.",
            })
        if not translation.strip():
            findings.append({
                "kind": "empty_translation",
                "severity": "error",
                "message": "ترجمه خالی است.",
            })

        source_tokens = token_counts(source)
        target_tokens = token_counts(translation)

        for token, count in sorted(source_tokens.items()):
            if target_tokens[token] < count:
                findings.append({
                    "kind": "missing_token",
                    "severity": "error",
                    "message": "متغیر، Placeholder یا Script Tag از ترجمه حذف شده است.",
                    "tokens": [token] * (count - target_tokens[token]),
                })
        for token, count in sorted(target_tokens.items()):
            if source_tokens[token] < count:
                findings.append({
                    "kind": "unexpected_token",
                    "severity": "error",
                    "message": "متغیر، Placeholder یا Script Tag اضافی در ترجمه دیده شد.",
                    "tokens": [token] * (count - source_tokens[token]),
                })

        if source.count("\n") != translation.count("\n"):
            findings.append({
                "kind": "newline_mismatch",
                "severity": "warning",
                "message": "ساختار شکست خط با متن مبدأ یکسان نیست.",
            })

        if source.startswith(" ") != translation.startswith(" ") or source.endswith(" ") != translation.endswith(" "):
            findings.append({
                "kind": "boundary_whitespace",
                "severity": "warning",
                "message": "فاصله ابتدا یا انتهای متن با متن مبدأ همخوان نیست.",
            })

        for term in glossary or []:
            if term.source.casefold() in source.casefold() and term.target not in translation:
                findings.append({
                    "kind": "glossary_consistency",
                    "severity": "warning",
                    "message": f"اصطلاح «{term.source}» با واژه‌نامه رسمی همخوان نیست.",
                    "source": term.source,
                    "suggestion": term.target,
                    "status": term.status,
                })

        return TranslationCheck(source=source, translation=translation, findings=findings)

    def check_and_record(self, store, translation_key: str, source: str, translation: str,
                         glossary: list[GlossaryTerm] | None = None) -> TranslationCheck:
        check = self.check(source, translation, glossary)
        store.record_qa_run(
            str(uuid4()), translation_key, source, translation, check.findings,
            datetime.now(timezone.utc).isoformat(),
        )
        return check

    def history(self, store, translation_key: str | None = None, limit: int = 20) -> list[dict]:
        return store.qa_runs(translation_key, limit)
