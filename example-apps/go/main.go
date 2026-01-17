package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"runtime"
	"time"
)

var startTime = time.Now()

type HealthResponse struct {
	Status  string  `json:"status"`
	Service string  `json:"service"`
	Uptime  float64 `json:"uptime"`
}

type InfoResponse struct {
	App         string            `json:"app"`
	Runtime     string            `json:"runtime"`
	Version     string            `json:"version"`
	Hostname    string            `json:"hostname"`
	Port        string            `json:"port"`
	Platform    string            `json:"platform"`
	Arch        string            `json:"arch"`
	Environment map[string]string `json:"environment"`
	Uptime      float64           `json:"uptime"`
}

func homeHandler(w http.ResponseWriter, r *http.Request) {
	hostname, _ := os.Hostname()
	port := getEnv("PORT", "8080")

	html := fmt.Sprintf(`
    <html>
        <head>
            <title>Vesla Test App - Go</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                    background: #f5f5f5;
                }
                .container {
                    background: white;
                    padding: 30px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                h1 { color: #2c3e50; }
                .info {
                    background: #ecf0f1;
                    padding: 15px;
                    border-radius: 4px;
                    margin: 10px 0;
                }
                .endpoint {
                    background: #00ADD8;
                    color: white;
                    padding: 8px 12px;
                    border-radius: 4px;
                    display: inline-block;
                    margin: 5px 0;
                    font-family: monospace;
                }
                .badge {
                    background: #00758D;
                    color: white;
                    padding: 4px 8px;
                    border-radius: 3px;
                    font-size: 0.9em;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Vesla Test Application <span class="badge">Go</span></h1>
                <p>This is a simple Go HTTP application for testing Vesla deployments.</p>

                <div class="info">
                    <strong>Runtime:</strong> Go %s<br>
                    <strong>Hostname:</strong> %s<br>
                    <strong>Port:</strong> %s<br>
                    <strong>Platform:</strong> %s/%s
                </div>

                <h2>Available Endpoints:</h2>
                <ul>
                    <li><span class="endpoint">GET /</span> - This page</li>
                    <li><span class="endpoint">GET /health</span> - Health check endpoint</li>
                    <li><span class="endpoint">GET /info</span> - JSON info about the app</li>
                </ul>
            </div>
        </body>
    </html>
    `, runtime.Version(), hostname, port, runtime.GOOS, runtime.GOARCH)

	w.Header().Set("Content-Type", "text/html")
	fmt.Fprint(w, html)
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	response := HealthResponse{
		Status:  "healthy",
		Service: "vesla-test-app-go",
		Uptime:  time.Since(startTime).Seconds(),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func infoHandler(w http.ResponseWriter, r *http.Request) {
	hostname, _ := os.Hostname()
	port := getEnv("PORT", "8080")

	response := InfoResponse{
		App:      "vesla-test-app",
		Runtime:  "go",
		Version:  runtime.Version(),
		Hostname: hostname,
		Port:     port,
		Platform: runtime.GOOS,
		Arch:     runtime.GOARCH,
		Environment: map[string]string{
			"PORT": port,
		},
		Uptime: time.Since(startTime).Seconds(),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func main() {
	port := getEnv("PORT", "8080")

	http.HandleFunc("/", homeHandler)
	http.HandleFunc("/health", healthHandler)
	http.HandleFunc("/info", infoHandler)

	addr := fmt.Sprintf("0.0.0.0:%s", port)
	log.Printf("Vesla Go test app listening on %s", addr)

	if err := http.ListenAndServe(addr, nil); err != nil {
		log.Fatal(err)
	}
}
