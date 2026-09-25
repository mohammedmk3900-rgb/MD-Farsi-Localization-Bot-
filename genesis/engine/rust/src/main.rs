use std::io::{self, Read};
use mdfarsi_qa::{validate_placeholders, validate_required_tokens};

fn main() {
    let mut input = String::new();
    io::stdin().read_to_string(&mut input).expect("read stdin");
    let mut parts = input.splitn(2, '\n');
    let source = parts.next().unwrap_or_default();
    let target = parts.next().unwrap_or_default();

    let result = validate_required_tokens(source, target)
        .and_then(|_| validate_placeholders(source, target));

    match result {
        Ok(()) => println!("{{\"schema_version\":1,\"operation\":\"qa\",\"status\":\"ok\",\"valid\":true}}"),
        Err(error) => println!("{{\"schema_version\":1,\"operation\":\"qa\",\"status\":\"failed\",\"valid\":false,\"error\":\"{}\"}}", error.replace('"', "\\\"")),
    }
}