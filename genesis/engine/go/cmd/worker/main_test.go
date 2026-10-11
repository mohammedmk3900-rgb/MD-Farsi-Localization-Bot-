package main

import (
	"strings"
	"testing"
)

func TestWorkerProducesVersionedResult(t *testing.T) {
	result := run(Job{Type: "discord_sync", ID: "test"})
	if result.SchemaVersion != 1 || result.Operation != "discord_sync" || result.Status != "ok" {
		t.Fatalf("unexpected result: %+v", result)
	}
}

func TestDecodeJobRejectsMalformedInput(t *testing.T) {
	if _, err := decodeJob(strings.NewReader("{")); err == nil {
		t.Fatal("malformed JSON must not become a successful default job")
	}
}

func TestDecodeJobRejectsMultipleJSONValues(t *testing.T) {
	if _, err := decodeJob(strings.NewReader("{} {}")); err == nil {
		t.Fatal("multiple JSON values must be rejected")
	}
}

func TestDecodeJobAcceptsOneJob(t *testing.T) {
	job, err := decodeJob(strings.NewReader("{\"type\":\"health\",\"id\":\"test\"}"))
	if err != nil {
		t.Fatal(err)
	}
	if job.Type != "health" || job.ID != "test" {
		t.Fatalf("unexpected decoded job: %+v", job)
	}
}

func TestDecodeJobRejectsJSONNull(t *testing.T) {
	if _, err := decodeJob(strings.NewReader("null")); err == nil {
		t.Fatal("null must not be accepted as a valid worker job")
	}
}
