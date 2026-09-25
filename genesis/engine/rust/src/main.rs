use std::io::{self, Read};
use mdfarsi_qa::validate_required_tokens;

fn main() {
    let mut input = String::new();
    io::stdin().read_to_string(&mut input).expect("read stdin");
    let mut parts = input.splitn(2, '\n');
    let source = parts.next().unwrap_or_default();
    let target = parts.next().unwrap_or_default();

    match validate_required_tokens(source, target) {
        Ok(()) => println!(r#"{{"valid":true}}"#),
        Err(error) => println!(r#"{{"valid":false,"error":"{}"}}"#, error.replace('"', "\"")),
    }
}
