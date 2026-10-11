use mdfarsi_qa::{validate_placeholders, validate_required_tokens};
use serde::Deserialize;
use std::io::{self, Read};

#[derive(Debug, Deserialize)]
struct Input {
    source: String,
    target: String,
}

fn parse_input(raw: &str) -> Result<Input, serde_json::Error> {
    serde_json::from_str(raw)
}

fn main() {
    let mut raw = String::new();
    io::stdin().read_to_string(&mut raw).expect("read stdin");
    let input = match parse_input(&raw) {
        Ok(input) => input,
        Err(error) => {
            eprintln!("invalid QA input JSON: {error}");
            std::process::exit(2);
        }
    };

    let result = validate_required_tokens(&input.source, &input.target)
        .and_then(|_| validate_placeholders(&input.source, &input.target));

    match result {
        Ok(()) => println!(
            "{{\"schema_version\":1,\"operation\":\"qa\",\"status\":\"ok\",\"valid\":true}}"
        ),
        Err(error) => {
            let escaped = error
                .replace('\\', "\\\\")
                .replace('"', "\\\"")
                .replace('\n', "\\n")
                .replace('\r', "\\r")
                .replace('\t', "\\t");
            println!(
                "{{\"schema_version\":1,\"operation\":\"qa\",\"status\":\"failed\",\"valid\":false,\"error\":\"{}\"}}",
                escaped
            );
            std::process::exit(2);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_multiline_source_and_target_as_json() {
        let raw = r#"{"source":"first\nsecond $NAME|H$","target":"اول\nدوم $NAME|H$"}"#;
        let input = parse_input(raw).expect("valid QA JSON");
        assert!(input.source.contains('\n'));
        assert!(input.target.contains('\n'));
        assert!(validate_placeholders(&input.source, &input.target).is_ok());
    }

    #[test]
    fn rejects_invalid_json_input() {
        assert!(parse_input("{").is_err());
    }
}
