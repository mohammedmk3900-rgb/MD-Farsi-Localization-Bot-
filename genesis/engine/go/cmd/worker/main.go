package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"
	"sync"
)

type Worker struct {
	mu      sync.Mutex
	queued  int
	handled uint64
}

type Health struct {
	Status  string `json:"status"`
	Queued  int    `json:"queued"`
	Handled uint64 `json:"handled"`
}

func (w *Worker) health(rw http.ResponseWriter, _ *http.Request) {
	w.mu.Lock()
	defer w.mu.Unlock()
	_ = json.NewEncoder(rw).Encode(Health{Status: "ok", Queued: w.queued, Handled: w.handled})
}

func main() {
	port := os.Getenv("GENESIS_GO_PORT")
	if port == "" { port = "8090" }
	worker := &Worker{}
	mux := http.NewServeMux()
	mux.HandleFunc("/health", worker.health)
	server := &http.Server{Addr: ":" + port, Handler: mux}
	log.Printf("genesis-go-worker listening on %s", port)
	log.Fatal(server.ListenAndServe())
}
