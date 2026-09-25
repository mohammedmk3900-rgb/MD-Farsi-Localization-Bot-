//! Deterministic, CPU-heavy analysis primitives for Genesis.

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PlaceholderIssue {
    pub source: String,
    pub translation: String,
    pub missing: Vec<String>,
    pub unexpected: Vec<String>,
}

fn placeholders(value: &str) -> Vec<String> {
    let bytes = value.as_bytes();
    let mut out = Vec::new();
    let mut i = 0;
    while i < bytes.len() {
        if bytes[i] == b'{' {
            if let Some(end) = value[i + 1..].find('}') {
                let end = i + 1 + end;
                if end > i + 1 {
                    out.push(value[i..=end].to_string());
                    i = end + 1;
                    continue;
                }
            }
        }
        i += 1;
    }
    out
}

pub fn check_placeholders(source: &str, translation: &str) -> PlaceholderIssue {
    let source_tokens = placeholders(source);
    let translation_tokens = placeholders(translation);
    let missing = source_tokens.iter()
        .filter(|token| !translation_tokens.contains(token))
        .cloned().collect();
    let unexpected = translation_tokens.iter()
        .filter(|token| !source_tokens.contains(token))
        .cloned().collect();
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
    fn detects_placeholder_drift() {
        let issue = check_placeholders("Hello {NAME}, {COUNTRY}", "سلام {NAME} {EXTRA}");
        assert_eq!(issue.missing, vec!["{COUNTRY}"]);
        assert_eq!(issue.unexpected, vec!["{EXTRA}"]);
    }

    #[test]
    fn accepts_matching_placeholders() {
        let issue = check_placeholders("Hello {NAME}", "سلام {NAME}");
        assert!(issue.missing.is_empty());
        assert!(issue.unexpected.is_empty());
    }
}
