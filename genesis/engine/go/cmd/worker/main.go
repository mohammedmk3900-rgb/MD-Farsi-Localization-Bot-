package main

import (
	"context"
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"syscall"
	"time"
)

type Job struct {
	ID        string         `json:"id"`
	Type      string         `json:"type"`
	Payload   map[string]any `json:"payload"`
	Status    string         `json:"status"`
	CreatedAt time.Time      `json:"created_at"`
	StartedAt *time.Time     `json:"started_at,omitempty"`
	EndedAt   *time.Time     `json:"ended_at,omitempty"`
	Result    map[string]any `json:"result,omitempty"`
	Error     string         `json:"error,omitempty"`
}

type JobRequest struct {
	Type    string         `json:"type"`
	Payload map[string]any `json:"payload"`
}

type Worker struct {
	mu      sync.RWMutex
	jobs    map[string]*Job
	queue   chan string
	handled atomic.Uint64
	workers int
}

type Health struct {
	Status   string `json:"status"`
	Queued   int    `json:"queued"`
	Running  int    `json:"running"`
	Handled  uint64 `json:"handled"`
	Workers  int    `json:"workers"`
}

func NewWorker(workerCount, queueSize int) *Worker {
	if workerCount < 1 { workerCount = 1 }
	if queueSize < 1 { queueSize = 64 }
	return &Worker{
		jobs:    make(map[string]*Job),
		queue:   make(chan string, queueSize),
		workers: workerCount,
	}
}

func (w *Worker) Start(ctx context.Context) {
	for i := 0; i < w.workers; i++ {
		go func() {
			for {
				select {
				case <-ctx.Done():
					return
				case id := <-w.queue:
					w.run(id)
				}
			}
		}()
	}
}

func (w *Worker) run(id string) {
	w.mu.Lock()
	job, ok := w.jobs[id]
	if !ok {
		w.mu.Unlock()
		return
	}
	now := time.Now().UTC()
	job.Status = "running"
	job.StartedAt = &now
	w.mu.Unlock()

	// Business rules stay in Python. Go owns concurrency and job lifecycle.
	result := map[string]any{
		"accepted": true,
		"job_type": job.Type,
		"payload_keys": len(job.Payload),
	}

	w.mu.Lock()
	end := time.Now().UTC()
	job.Status = "completed"
	job.EndedAt = &end
	job.Result = result
	w.mu.Unlock()
	w.handled.Add(1)
}

func (w *Worker) enqueue(req JobRequest) (*Job, error) {
	typ := strings.TrimSpace(req.Type)
	if typ == "" { return nil, errors.New("job type is required") }

	id := strconv.FormatInt(time.Now().UnixNano(), 10)
	job := &Job{
		ID: id, Type: typ, Payload: req.Payload,
		Status: "queued", CreatedAt: time.Now().UTC(),
	}
	w.mu.Lock()
	w.jobs[id] = job
	w.mu.Unlock()

	select {
	case w.queue <- id:
		return job, nil
	default:
		w.mu.Lock()
		delete(w.jobs, id)
		w.mu.Unlock()
		return nil, errors.New("worker queue is full")
	}
}

func (w *Worker) health(rw http.ResponseWriter, _ *http.Request) {
	w.mu.RLock()
	queued, running := 0, 0
	for _, job := range w.jobs {
		switch job.Status {
		case "queued": queued++
		case "running": running++
		}
	}
	w.mu.RUnlock()

	writeJSON(rw, http.StatusOK, Health{
		Status: "ok", Queued: queued, Running: running,
		Handled: w.handled.Load(), Workers: w.workers,
	})
}

func (w *Worker) createJob(rw http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSON(rw, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
		return
	}
	var req JobRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(rw, http.StatusBadRequest, map[string]string{"error": "invalid JSON"})
		return
	}
	job, err := w.enqueue(req)
	if err != nil {
		writeJSON(rw, http.StatusServiceUnavailable, map[string]string{"error": err.Error()})
		return
	}
	writeJSON(rw, http.StatusAccepted, job)
}

func (w *Worker) getJob(rw http.ResponseWriter, r *http.Request) {
	id := strings.TrimPrefix(r.URL.Path, "/jobs/")
	if id == "" || id == r.URL.Path {
		writeJSON(rw, http.StatusBadRequest, map[string]string{"error": "job id is required"})
		return
	}
	w.mu.RLock()
	job, ok := w.jobs[id]
	w.mu.RUnlock()
	if !ok {
		writeJSON(rw, http.StatusNotFound, map[string]string{"error": "job not found"})
		return
	}
	writeJSON(rw, http.StatusOK, job)
}

func writeJSON(rw http.ResponseWriter, status int, value any) {
	rw.Header().Set("Content-Type", "application/json")
	rw.WriteHeader(status)
	_ = json.NewEncoder(rw).Encode(value)
}

func main() {
	port := os.Getenv("GENESIS_GO_PORT")
	if port == "" { port = "8090" }
	workerCount, _ := strconv.Atoi(os.Getenv("GENESIS_GO_WORKERS"))
	queueSize, _ := strconv.Atoi(os.Getenv("GENESIS_GO_QUEUE_SIZE"))
	worker := NewWorker(workerCount, queueSize)

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	worker.Start(ctx)

	mux := http.NewServeMux()
	mux.HandleFunc("/health", worker.health)
	mux.HandleFunc("/jobs", worker.createJob)
	mux.HandleFunc("/jobs/", worker.getJob)

	server := &http.Server{
		Addr:              ":" + port,
		Handler:           mux,
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       10 * time.Second,
		WriteTimeout:      10 * time.Second,
		IdleTimeout:       60 * time.Second,
	}
	go func() {
		<-ctx.Done()
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		_ = server.Shutdown(shutdownCtx)
	}()

	log.Printf("genesis-go-worker listening on %s with %d workers", port, worker.workers)
	if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		log.Fatal(err)
	}
}
