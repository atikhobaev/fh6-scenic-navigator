package launcher_native

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestProbeHealthAndTelemetry(t *testing.T) {
	mux := http.NewServeMux()
	mux.HandleFunc("/api/info", func(w http.ResponseWriter, r *http.Request) {
		json.NewEncoder(w).Encode(map[string]any{"name": "FH6 Scenic Navigator", "version": "1.19.0", "lanIp": "192.168.1.4", "httpPort": 8080, "udpPort": 1234})
	})
	mux.HandleFunc("/api/telemetry", func(w http.ResponseWriter, r *http.Request) {
		json.NewEncoder(w).Encode(map[string]any{"connected": true, "ageMs": 17})
	})
	s := httptest.NewServer(mux)
	defer s.Close()
	h, err := ProbeHealth(s.URL)
	if err != nil || h.Version != "1.19.0" {
		t.Fatalf("%+v %v", h, err)
	}
	tele, err := ProbeTelemetry(s.URL)
	if err != nil || !tele.Connected {
		t.Fatalf("%+v %v", tele, err)
	}
}
