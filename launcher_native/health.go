package launcher_native

import (
	"encoding/json"
	"fmt"
	"net/http"
	"time"
)

type Health struct {
	Name, Version, LANIP string
	HTTPPort, UDPPort    int
}
type Telemetry struct {
	Connected bool `json:"connected"`
	AgeMs     *int `json:"ageMs"`
}

func getJSON(url string, v any) error {
	c := &http.Client{Timeout: 750 * time.Millisecond}
	r, e := c.Get(url)
	if e != nil {
		return e
	}
	defer r.Body.Close()
	if r.StatusCode != 200 {
		return fmt.Errorf("HTTP %d", r.StatusCode)
	}
	return json.NewDecoder(r.Body).Decode(v)
}
func ProbeHealth(base string) (Health, error) {
	var raw struct {
		Name     string `json:"name"`
		Version  string `json:"version"`
		LANIP    string `json:"lanIp"`
		HTTPPort int    `json:"httpPort"`
		UDPPort  int    `json:"udpPort"`
	}
	e := getJSON(base+"/api/info", &raw)
	return Health{raw.Name, raw.Version, raw.LANIP, raw.HTTPPort, raw.UDPPort}, e
}
func ProbeTelemetry(base string) (Telemetry, error) {
	var t Telemetry
	e := getJSON(base+"/api/telemetry", &t)
	return t, e
}
