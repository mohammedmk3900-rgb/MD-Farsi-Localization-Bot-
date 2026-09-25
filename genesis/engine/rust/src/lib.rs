pub fn validate_required_tokens(source: &str, target: &str) -> Result<(), String> {
    for token in ["$COUNTRY", "$NAME", "£fuel_texticon"] {
        if source.contains(token) && !target.contains(token) {
            return Err(format!("missing required token: {token}"));
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn preserves_required_tokens() {
        assert!(validate_required_tokens(
            "$COUNTRY has £fuel_texticon",
            "$COUNTRY دارای £fuel_texticon است"
        ).is_ok());
    }

    #[test]
    fn detects_missing_tokens() {
        assert!(validate_required_tokens("$COUNTRY has £fuel_texticon", "$COUNTRY دارد").is_err());
    }
}
