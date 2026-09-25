$ErrorActionPreference = "Stop"
$Root = git rev-parse --show-toplevel
Set-Location $Root
cargo test --manifest-path genesis/engine/rust/Cargo.toml
go test ./genesis/engine/go/...
cmake -S genesis/engine/cpp -B build/native
cmake --build build/native
