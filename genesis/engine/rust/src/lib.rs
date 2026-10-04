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
    let chars: Vec<(usize, char)> = text.char_indices().collect();
    let mut tokens = HashSet::new();
    let mut index = 0;

    while index < chars.len() {
        let (start, marker) = chars[index];

        if matches!(marker, '$' | '£' | '§') {
            let mut end = index + 1;
            while end < chars.len()
                && (chars[end].1.is_ascii_alphanumeric() || matches!(chars[end].1, '_' | '!'))
            {
                end += 1;
            }

            if end > index + 1 {
                let end_byte = if end < chars.len() { chars[end].0 } else { text.len() };
                tokens.insert(text[start..end_byte].to_string());
            }
            index = end;
        } else if marker == '[' {
            let mut end = index + 1;
            while end < chars.len()
                && chars[end].1 != ']'
                && chars[end].1 != '\n'
                && chars[end].1 != '\r'
            {
                end += 1;
            }

            if end < chars.len() && chars[end].1 == ']' {
                let end_byte = chars[end].0 + chars[end].1.len_utf8();
                tokens.insert(text[start..end_byte].to_string());
                index = end + 1;
            } else {
                index += 1;
            }
        } else {
            index += 1;
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
    fn accepts_matching_placeholders_and_control_tokens() {
        assert!(
            validate_placeholders(
                "$COUNTRY £fuel_texticon §Y[scope_tag]",
                "$COUNTRY £fuel_texticon §Y[scope_tag]"
            )
            .is_ok()
        );
    }

    #[test]
    fn detects_changed_placeholder_set() {
        assert!(validate_placeholders("$COUNTRY $NAME", "$COUNTRY").is_err());
    }

    #[test]
    fn detects_changed_control_or_scope_tokens() {
        assert!(
            validate_placeholders(
                "$COUNTRY §Y[scope_tag]",
                "$COUNTRY §![scope_tag]"
            )
            .is_err()
        );
    }
}
