from __future__ import annotations

import re

from app.domain.models import GlossaryTerm, TranslationCheck

TOKEN_PATTERNS = (
    re.compile(r"\$[^\s$]+"),
    re.compile(r"\[[^\]]+\]"),
    re.compile(r"§[A-Za-z0-9_]+"),
    re.compile(r"£[A-Za-z0-9_]+"),
)


def tokens(text: str) -> set[str]:
    return {token for pattern in TOKEN_PATTERNS for token in pattern.findall(text)}


class TranslationService:
    """Deterministic translation safety checks. Never publishes translations."""

    def __init__(self, engine=None):
        self.engine = engine

    def check(
        self,
        source: str,
        translation: str,
        glossary: list[GlossaryTerm] | None = None,
    ) -> TranslationCheck:
        findings: list[dict] = []
        source_tokens = tokens(source)
        target_tokens = tokens(translation)

        if self.engine is not None:
            try:
                result = self.engine.check_translation(source, translation)
                source_tokens = source_tokens | set(result.missing) | set(result.unexpected)
                target_tokens = target_tokens | set(result.unexpected)
                # Rebuild the exact token drift from the Rust engine's result.
                missing = sorted(result.missing)
                unexpected = sorted(result.unexpected)
            except (OSError, RuntimeError, ValueError):
                missing = sorted(source_tokens - target_tokens)
                unexpected = sorted(target_tokens - source_tokens)
        else:
            missing = sorted(source_tokens - target_tokens)
            unexpected = sorted(target_tokens - source_tokens)

        if missing:
            findings.append({
                "kind": "missing_token",
                "message": "متغیر، Placeholder یا Script Tag از ترجمه حذف شده است.",
                "tokens": missing,
            })
        if unexpected:
            findings.append({
                "kind": "unexpected_token",
                "message": "متغیر، Placeholder یا Script Tag اضافی در ترجمه دیده شد.",
                "tokens": unexpected,
            })

        for term in glossary or []:
            if term.source.casefold() in source.casefold() and term.target not in translation:
                findings.append({
                    "kind": "glossary_consistency",
                    "message": f"اصطلاح «{term.source}» با واژه‌نامه رسمی همخوان نیست.",
                    "source": term.source,
                    "suggestion": term.target,
                    "status": term.status,
                })

        return TranslationCheck(source=source, translation=translation, findings=findings)
