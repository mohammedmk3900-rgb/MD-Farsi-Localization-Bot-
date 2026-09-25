package main

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestHealth(t *testing.T) {
	w := NewWorker(2, 4)
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	rec := httptest.NewRecorder()
	w.health(rec, req)
	if rec.Code != http.StatusOK { t.Fatalf("expected 200, got %d", rec.Code) }
	var health Health
	if err := json.NewDecoder(rec.Body).Decode(&health); err != nil { t.Fatal(err) }
	if health.Status != "ok" || health.Workers != 2 { t.Fatalf("unexpected health: %+v", health) }
}

func TestJobLifecycle(t *testing.T) {
	w := NewWorker(1, 4)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	w.Start(ctx)

	job, err := w.enqueue(JobRequest{Type: "paratranz.sync", Payload: map[string]any{"project_id": 19621}})
	if err != nil { t.Fatal(err) }
	if job.Status != "queued" { t.Fatalf("expected queued, got %s", job.Status) }

	deadline := time.Now().Add(time.Second)
	for time.Now().Before(deadline) {
		w.mu.RLock()
		status := w.jobs[job.ID].Status
		w.mu.RUnlock()
		if status == "completed" { return }
		time.Sleep(5 * time.Millisecond)
	}
	t.Fatal("job did not complete")
}
