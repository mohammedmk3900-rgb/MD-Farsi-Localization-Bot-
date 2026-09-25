//! Deterministic translation-token analysis for Genesis.

use std::collections::BTreeSet;
use serde::Serialize;

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct PlaceholderIssue {
    pub source: String,
    pub translation: String,
    pub missing: Vec<String>,
    pub unexpected: Vec<String>,
}

fn token_set(value: &str) -> BTreeSet<String> {
    let mut out = BTreeSet::new();
    let chars: Vec<char> = value.chars().collect();
    let mut i = 0;

    while i < chars.len() {
        let (open, close) = match chars[i] {
            '$' => ('$', '$'),
            '[' => ('[', ']'),
            '{' => ('{', '}'),
            '§' => ('§', ' '),
            '£' => ('£', ' '),
            _ => { i += 1; continue; }
        };

        if open == '§' || open == '£' {
            let start = i;
            i += 1;
            while i < chars.len() && !chars[i].is_whitespace() {
                i += 1;
            }
            if i > start + 1 {
                out.insert(chars[start..i].iter().collect());
            }
            continue;
        }

        let start = i;
        i += 1;
        while i < chars.len() && chars[i] != close {
            i += 1;
        }
        if i < chars.len() && i > start + 1 {
            i += 1;
            out.insert(chars[start..i].iter().collect());
        }
    }
    out
}

pub fn check_placeholders(source: &str, translation: &str) -> PlaceholderIssue {
    let source_tokens = token_set(source);
    let translation_tokens = token_set(translation);
    let missing = source_tokens.difference(&translation_tokens).cloned().collect();
    let unexpected = translation_tokens.difference(&source_tokens).cloned().collect();

    PlaceholderIssue {
        source: source.to_string(),
        translation: translation.to_string(),
        missing,
        unexpected,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn detects_md_tokens() {
        let issue = check_placeholders(
            "$NAME|H$ [ROOT.GetName] £fuel_texticon §R {COUNT}",
            "$NAME|H$ [ROOT.GetName] §R {EXTRA}",
        );
        assert!(issue.missing.contains(&"£fuel_texticon".to_string()));
        assert!(issue.missing.contains(&"{COUNT}".to_string()));
        assert!(issue.unexpected.contains(&"{EXTRA}".to_string()));
    }

    #[test]
    fn accepts_matching_tokens() {
        let issue = check_placeholders(
            "$COUNTRY|Y$ [ROOT.GetName] £fuel_texticon §G",
            "$COUNTRY|Y$ [ROOT.GetName] £fuel_texticon §G",
        );
        assert!(issue.missing.is_empty());
        assert!(issue.unexpected.is_empty());
    }
}
