#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
cargo test --manifest-path genesis/engine/rust/Cargo.toml
go test ./genesis/engine/go/...
cmake -S genesis/engine/cpp -B build/native
cmake --build build/native
