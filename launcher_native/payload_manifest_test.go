package launcher_native

import (
	"archive/zip"
	"bytes"
	"os"
	"testing"
)

func TestEmbeddedPayloadContainsServerAndNoBAT(t *testing.T) {
	zr, err := zip.NewReader(bytes.NewReader(EmbeddedAppPayload), int64(len(EmbeddedAppPayload)))
	if err != nil {
		t.Fatal(err)
	}
	seenServer := false
	for _, f := range zr.File {
		if f.Name == "server.py" {
			seenServer = true
		}
		if len(f.Name) >= 4 && f.Name[len(f.Name)-4:] == ".bat" {
			t.Fatalf("BAT leaked: %s", f.Name)
		}
	}
	if !seenServer {
		t.Fatal("server.py missing")
	}
}

func TestReleaseBuildRequiresEmbeddedPythonRuntime(t *testing.T) {
	if os.Getenv("FH6_RELEASE_VERIFY") != "1" {
		t.Skip("release-only embedded runtime gate")
	}
	if len(EmbeddedPythonZip) < 10_000_000 {
		t.Fatalf("embedded CPython runtime missing: %d bytes", len(EmbeddedPythonZip))
	}
}
