use std::collections::HashSet;

pub fn validate_required_tokens(source: &str, target: &str) -> Result<(), String> {
    for token in ["$COUNTRY", "$NAME", "£fuel_texticon"] {
        if source.contains(token) && !target.contains(token) {
            return Err(format!("missing required token: {token}"));
        }
    }
    Ok(())
}

pub fn validate_placeholders(source: &str, target: &str) -> Result<(), String> {
    if extract_tokens(source) != extract_tokens(target) {
        return Err("placeholder set changed".to_string());
    }
    Ok(())
}

fn extract_tokens(text: &str) -> HashSet<String> {
    let mut tokens = HashSet::new();
    let bytes = text.as_bytes();
    let mut i = 0;
    while i < bytes.len() {
        if bytes[i] == b'$' {
            let start = i;
            i += 1;
            while i < bytes.len() && (bytes[i].is_ascii_alphanumeric() || bytes[i] == b'_') {
                i += 1;
            }
            if i > start + 1 {
                tokens.insert(text[start..i].to_string());
            }
        } else {
            i += 1;
        }
    }
    tokens
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn detects_missing_required_tokens() {
        assert!(validate_required_tokens("$COUNTRY has £fuel_texticon", "$COUNTRY دارد").is_err());
    }

    #[test]
    fn accepts_matching_placeholders() {
        assert!(validate_placeholders("$COUNTRY $NAME", "$COUNTRY $NAME").is_ok());
    }

    #[test]
    fn detects_changed_placeholder_set() {
        assert!(validate_placeholders("$COUNTRY $NAME", "$COUNTRY").is_err());
    }
}
