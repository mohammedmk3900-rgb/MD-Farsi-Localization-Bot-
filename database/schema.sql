CREATE TABLE IF NOT EXISTS operations (
    id INTEGER PRIMARY KEY,
    operation TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ok', 'failed', 'skipped')),
    generated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_operations_generated_at
ON operations(generated_at);
