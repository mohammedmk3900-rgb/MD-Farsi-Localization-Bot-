package main

import "testing"

func TestWorkerDefaults(t *testing.T) {
    if Job{Type: "health", ID: "test"}.Type != "health" {
        t.Fatal("unexpected job type")
    }
}
