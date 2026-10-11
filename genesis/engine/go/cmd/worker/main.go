package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"time"
)

type Job struct {
	Type    string         `json:"type"`
	ID      string         `json:"id"`
	Payload map[string]any `json:"payload,omitempty"`
}

type Result struct {
	SchemaVersion int            `json:"schema_version"`
	Operation     string         `json:"operation"`
	Status        string         `json:"status"`
	GeneratedAt   string         `json:"generated_at"`
	JobID         string         `json:"job_id"`
	Payload       map[string]any `json:"payload,omitempty"`
}

func run(job Job) Result {
	if job.Type == "" {
		job.Type = "health"
	}
	if job.ID == "" {
		job.ID = fmt.Sprintf("job-%d", time.Now().UnixNano())
	}

	return Result{
		SchemaVersion: 1,
		Operation:     job.Type,
		Status:        "ok",
		GeneratedAt:   time.Now().UTC().Format(time.RFC3339),
		JobID:         job.ID,
		Payload:       job.Payload,
	}
}

func decodeJob(reader io.Reader) (Job, error) {
	var raw json.RawMessage
	decoder := json.NewDecoder(reader)
	if err := decoder.Decode(&raw); err != nil {
		return Job{}, err
	}
	if len(raw) == 0 || raw[0] != '{' {
		return Job{}, errors.New("worker input must be a JSON object")
	}
	var job Job
	if err := json.Unmarshal(raw, &job); err != nil {
		return Job{}, err
	}
	var trailing any
	if err := decoder.Decode(&trailing); err != io.EOF {
		if err == nil {
			return Job{}, errors.New("multiple JSON values in worker input")
		}
		return Job{}, err
	}
	return job, nil
}

func main() {
	job, err := decodeJob(os.Stdin)
	if err != nil {
		fmt.Fprintln(os.Stderr, "invalid worker input:", err)
		os.Exit(2)
	}
	if err := json.NewEncoder(os.Stdout).Encode(run(job)); err != nil {
		fmt.Fprintln(os.Stderr, "failed to encode worker result:", err)
		os.Exit(2)
	}
}
