use std::io::{self, Read};
use genesis_engine::check_placeholders;

fn main() {
    let mut input = String::new();
    io::stdin().read_to_string(&mut input).expect("read stdin");
    let mut lines = input.lines();
    let source = lines.next().unwrap_or_default();
    let translation = lines.next().unwrap_or_default();
    let result = check_placeholders(source, translation);
    println!("missing={} unexpected={}", result.missing.len(), result.unexpected.len());
}
