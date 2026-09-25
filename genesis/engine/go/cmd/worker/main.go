package main

import (
    "encoding/json"
    "fmt"
    "os"
    "time"
)

type Job struct {
    Type string `json:"type"`
    ID string `json:"id"`
    Payload map[string]any `json:"payload,omitempty"`
}

type Result struct {
    SchemaVersion int `json:"schema_version"`
    Operation string `json:"operation"`
    Status string `json:"status"`
    GeneratedAt string `json:"generated_at"`
    JobID string `json:"job_id"`
    Payload map[string]any `json:"payload,omitempty"`
}

func run(job Job) Result {
    if job.Type == "" { job.Type = "health" }
    if job.ID == "" { job.ID = fmt.Sprintf("job-%d", time.Now().UnixNano()) }
    return Result{SchemaVersion: 1, Operation: job.Type, Status: "ok", GeneratedAt: time.Now().UTC().Format(time.RFC3339), JobID: job.ID, Payload: job.Payload}
}

func main() {
    var job Job
    if err := json.NewDecoder(os.Stdin).Decode(&job); err != nil { job = Job{} }
    _ = json.NewEncoder(os.Stdout).Encode(run(job))
}