from __future__ import annotations

import re
from dataclasses import dataclass


_TOKEN_PATTERNS = (
    r"\$[^\s$]+",
    r"\[[^\]]+\]",
    r"§[A-Za-z0-9_]+",
    r"£[A-Za-z0-9_]+",
)


@dataclass(frozen=True)
class Finding:
    kind: str
    message: str
    source: str | None = None
    suggestion: str | None = None


class TranslationAssistant:
    """Human-in-the-loop translation checker; it never publishes translations."""

    def _tokens(self, text: str) -> set[str]:
        return {token for pattern in _TOKEN_PATTERNS for token in re.findall(pattern, text)}

    def check(
        self,
        source: str,
        translation: str,
        glossary: list[dict] | None = None,
    ) -> dict:
        findings: list[dict] = []
        source_tokens = self._tokens(source)
        translation_tokens = self._tokens(translation)

        missing = sorted(source_tokens - translation_tokens)
        unexpected = sorted(translation_tokens - source_tokens)

        if missing:
            findings.append({
                "kind": "broken_placeholder",
                "message": "متغیر یا Placeholder از متن اصلی حذف شده است.",
                "tokens": missing,
            })
        if unexpected:
            findings.append({
                "kind": "unexpected_placeholder",
                "message": "متغیر یا Placeholder اضافی در ترجمه دیده شد.",
                "tokens": unexpected,
            })

        normalized = translation.strip()
        glossary_matches: list[dict] = []
        for term in glossary or []:
            source_term = str(term.get("term") or term.get("source") or term.get("key") or "").strip()
            target = str(term.get("translation") or term.get("target") or term.get("value") or "").strip()
            if source_term and target and source_term.lower() in source.lower():
                glossary_matches.append({"source": source_term, "target": target})
                if target not in normalized:
                    findings.append({
                        "kind": "glossary_consistency",
                        "message": f"اصطلاح «{source_term}» با واژه‌نامه رسمی همخوان نیست.",
                        "source": source_term,
                        "suggestion": target,
                    })

        return {
            "approved": not findings,
            "publish": False,
            "findings": findings,
            "glossary_matches": glossary_matches,
            "source_tokens": sorted(source_tokens),
            "translation_tokens": sorted(translation_tokens),
        }
