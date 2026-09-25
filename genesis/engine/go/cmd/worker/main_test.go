package main

import "testing"

func TestWorkerProducesVersionedResult(t *testing.T) {
    result := run(Job{Type: "discord_sync", ID: "test"})
    if result.SchemaVersion != 1 || result.Operation != "discord_sync" || result.Status != "ok" {
        t.Fatalf("unexpected result: %+v", result)
    }
}
