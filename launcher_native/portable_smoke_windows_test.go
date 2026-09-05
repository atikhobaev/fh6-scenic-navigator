//go:build windows

package launcher_native

import (
	"context"
	"encoding/binary"
	"io"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

// Explicit release integration gate: uses real embedded Python and server, with no system Python.
func TestPortableControllerWithoutSystemPython(t *testing.T) {
	if os.Getenv("FH6_PORTABLE_SMOKE") != "1" {
		t.Skip("opt-in portable integration smoke")
	}
	if len(EmbeddedPythonZip) < 10_000_000 {
		t.Fatal("verified embedded Python required")
	}
	t.Setenv("LOCALAPPDATA", t.TempDir())
	t.Setenv("PATH", filepath.Join(os.Getenv("SystemRoot"), "System32"))
	t.Setenv("FH6_PYTHON", "")
	if path, err := ResolvePython(envMap()); err == nil {
		t.Fatalf("system Python unexpectedly available: %s", path)
	}
	c := NewController(nil)
	c.Settings.AutoOpenDrive = false
	c.Settings.HTTPPort = 18081
	c.Settings.UDPPort = 1234
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	defer c.Stop()
	c.start(ctx)
	h, err := ProbeHealth("http://127.0.0.1:18081")
	if err != nil || h.Version != AppVersion || h.UDPPort != 1234 {
		t.Fatalf("startup: %#v %v; logs %v", h, err, c.Logs())
	}
	for _, path := range []string{"/", "/planner/"} {
		response, err := http.Get("http://127.0.0.1:18081" + path)
		if err != nil {
			t.Fatal(err)
		}
		body, err := io.ReadAll(response.Body)
		response.Body.Close()
		if err != nil || response.StatusCode != 200 || !strings.Contains(string(body), "v"+AppVersion) {
			t.Fatalf("UI response %s: %v", path, err)
		}
	}
	socket, err := net.Dial("udp", "127.0.0.1:1234")
	if err != nil {
		t.Fatal(err)
	}
	packet := make([]byte, 323)
	binary.LittleEndian.PutUint32(packet, 1)
	_, err = socket.Write(packet)
	socket.Close()
	if err != nil {
		t.Fatal(err)
	}
	time.Sleep(150 * time.Millisecond)
	telemetry, err := ProbeTelemetry("http://127.0.0.1:18081")
	if err != nil || !telemetry.Connected {
		t.Fatalf("UDP telemetry: %#v %v", telemetry, err)
	}
	c.Stop()
	cancel()
	if _, err := ProbeHealth("http://127.0.0.1:18081"); err == nil {
		t.Fatal("orphan HTTP server after Stop")
	}
	listener, err := net.Listen("tcp", "127.0.0.1:18081")
	if err != nil {
		t.Fatal(err)
	}
	listener.Close()
	udp, err := net.ListenPacket("udp", "127.0.0.1:1234")
	if err != nil {
		t.Fatal(err)
	}
	udp.Close()
}
