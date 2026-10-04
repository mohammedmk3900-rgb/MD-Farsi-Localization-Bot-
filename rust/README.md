# 🦀 MD Farsi Rust Engine

The Rust layer is now a real deterministic validation engine.

## Responsibility

- Validate Paradox/HOI4 localization tokens before release.
- Detect changed $...$, £... and §...§ token sequences.
- Provide a fast, memory-safe CLI suitable for large batch validation.
- Stay independent from Discord, GitHub and secrets.

## Contract

Read one JSON object from stdin:

~~~json
{"source":"...","target":"..."}
~~~

The process prints a JSON validation report and exits with 0 when valid and 2 when a protected token sequence differs.

Python remains the orchestration layer; Rust owns deterministic hot-path validation.
