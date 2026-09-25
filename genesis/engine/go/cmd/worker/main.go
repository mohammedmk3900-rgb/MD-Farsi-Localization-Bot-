package main

import (
    "encoding/json"
    "fmt"
    "os"
    "time"
)

type Job struct {
    Type string
    ID   string
}

type Result struct {
    ID          string
    Status      string
    CompletedAt string
}

func main() {
    jobType := os.Getenv("MD_JOB_TYPE")
    if jobType == "" {
        jobType = "health"
    }
    job := Job{Type: jobType, ID: fmt.Sprintf("job-%d", time.Now().UnixNano())}
    result := Result{ID: job.ID, Status: "accepted", CompletedAt: time.Now().UTC().Format(time.RFC3339)}
    _ = json.NewEncoder(os.Stdout).Encode(result)
}
