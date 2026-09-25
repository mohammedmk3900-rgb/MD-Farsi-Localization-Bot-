use std::io::{self, Read};
use genesis_engine::check_placeholders;
use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize)]
struct CheckRequest {
    source: String,
    translation: String,
}

#[derive(Debug, Serialize)]
struct CheckResponse {
    missing: Vec<String>,
    unexpected: Vec<String>,
}

fn main() {
    let mut input = String::new();
    io::stdin().read_to_string(&mut input).expect("read stdin");
    let request: CheckRequest = serde_json::from_str(&input).expect("invalid JSON");
    let result = check_placeholders(&request.source, &request.translation);
    let response = CheckResponse { missing: result.missing, unexpected: result.unexpected };
    println!("{}", serde_json::to_string(&response).expect("serialize response"));
}
