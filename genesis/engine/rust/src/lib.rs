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

fn extract_tokens(text: &str) -> Vec<String> {
    let mut tokens = Vec::new();
    let mut i = 0;

    while i < text.len() {
        let rest = &text[i..];

        if rest.starts_with('$') {
            if let Some(relative_end) = rest[1..].find('$') {
                let end = i + 1 + relative_end;
                let body = &text[i + 1..end];
                if !body.is_empty() && !body.chars().any(char::is_whitespace) {
                    tokens.push(text[i..=end].to_string());
                    i = end + 1;
                    continue;
                }
            }
        }

        if rest.starts_with('[') {
            if let Some(relative_end) = rest.find(']') {
                if relative_end > 1 {
                    let end = i + relative_end;
                    tokens.push(text[i..=end].to_string());
                    i = end + 1;
                    continue;
                }
            }
        }

        if rest.starts_with('§') {
            let after_symbol = i + '§'.len_utf8();
            let after = &text[after_symbol..];
            if after.starts_with('!') {
                tokens.push(text[i..=after_symbol].to_string());
                i = after_symbol + 1;
                continue;
            }

            let mut end = after_symbol;
            while end < text.len() {
                let byte = text.as_bytes()[end];
                if byte.is_ascii_alphanumeric() || byte == b'_' {
                    end += 1;
                } else {
                    break;
                }
            }
            if end > after_symbol {
                tokens.push(text[i..end].to_string());
                i = end;
                continue;
            }
        }

        if rest.starts_with('£') {
            let after_symbol = i + '£'.len_utf8();
            let mut end = after_symbol;
            while end < text.len() {
                let byte = text.as_bytes()[end];
                if byte.is_ascii_alphanumeric() || byte == b'_' {
                    end += 1;
                } else {
                    break;
                }
            }
            if end > after_symbol {
                tokens.push(text[i..end].to_string());
                i = end;
                continue;
            }
        }

        let ch = rest.chars().next().expect("index is within string");
        i += ch.len_utf8();
    }

    tokens.sort();
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
        let text = "$COUNTRY$ $NAME$";
        assert!(validate_placeholders(text, text).is_ok());
    }

    #[test]
    fn detects_changed_placeholder_set() {
        assert!(validate_placeholders("$COUNTRY$ $NAME$", "$COUNTRY$").is_err());
    }

    #[test]
    fn preserves_complete_hoi4_tokens_and_allows_reordering() {
        let source = "$NAME|H$ [ROOT.GetName] §Y §! £fuel_texticon";
        let target = "£fuel_texticon §! [ROOT.GetName] $NAME|H$ §Y";
        assert!(validate_placeholders(source, target).is_ok());
    }

    #[test]
    fn detects_changed_modifiers_and_duplicate_tokens() {
        assert!(validate_placeholders("$NAME|H$", "$NAME|B$").is_err());
        assert!(validate_placeholders("$NAME$", "$NAME$ $NAME$").is_err());
    }
}
