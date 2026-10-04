use regex::Regex;
use serde::{Deserialize, Serialize};
use std::io::{self, Read};

#[derive(Debug, Deserialize)]
struct Input { source: String, target: String }

#[derive(Debug, Serialize)]
struct Report { valid: bool, checks: Vec<Check> }

#[derive(Debug, Serialize)]
struct Check { name: &'static str, passed: bool, detail: String }

fn captures(text: &str, pattern: &Regex) -> Vec<String> {
    pattern.captures_iter(text).map(|c| c.get(0).unwrap().as_str().to_string()).collect()
}

fn main() {
    let mut raw = String::new();
    io::stdin().read_to_string(&mut raw).expect("stdin");
    let input: Input = serde_json::from_str(&raw).expect("input JSON");

    let dollar = Regex::new(r"\$[^$\n]+\$").unwrap();
    let icon = Regex::new(r"£[A-Za-z0-9_]+").unwrap();
    // HOI4 color/control codes such as §Y and §!.
    let control = Regex::new(r"§[A-Za-z0-9!]").unwrap();

    let source_dollar = captures(&input.source, &dollar);
    let target_dollar = captures(&input.target, &dollar);
    let source_icon = captures(&input.source, &icon);
    let target_icon = captures(&input.target, &icon);
    let source_control = captures(&input.source, &control);
    let target_control = captures(&input.target, &control);

    let checks = vec![
        Check { name: "dollar_tokens", passed: source_dollar == target_dollar, detail: format!("source={} target={}", source_dollar.len(), target_dollar.len()) },
        Check { name: "icon_tokens", passed: source_icon == target_icon, detail: format!("source={} target={}", source_icon.len(), target_icon.len()) },
        Check { name: "control_codes", passed: source_control == target_control, detail: format!("source={} target={}", source_control.len(), target_control.len()) },
    ];

    let valid = checks.iter().all(|c| c.passed);
    println!("{}", serde_json::to_string(&Report { valid, checks }).unwrap());
    if !valid { std::process::exit(2); }
}
