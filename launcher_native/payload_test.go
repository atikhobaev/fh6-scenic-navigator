package launcher_native

import (
	"archive/zip"
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"os"
	"path/filepath"
	"testing"
)

func tinyZip(t *testing.T) []byte {
	var b bytes.Buffer
	z := zip.NewWriter(&b)
	w, _ := z.Create("server.py")
	w.Write([]byte("print('ok')"))
	z.Close()
	return b.Bytes()
}
func TestExtractPayloadVersionMarker(t *testing.T) {
	d := t.TempDir()
	if err := ExtractPayload(tinyZip(t), d, "1.19.0"); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(filepath.Join(d, "server.py")); err != nil {
		t.Fatal(err)
	}
	b, err := os.ReadFile(filepath.Join(d, ".payload-version"))
	if err != nil || string(b) != "1.19.0" {
		t.Fatalf("marker=%q err=%v", b, err)
	}
}
func TestVerifySHA256(t *testing.T) {
	p := filepath.Join(t.TempDir(), "x")
	os.WriteFile(p, []byte("abc"), 0644)
	h := sha256.Sum256([]byte("abc"))
	if err := VerifySHA256(p, hex.EncodeToString(h[:])); err != nil {
		t.Fatal(err)
	}
	if VerifySHA256(p, "00") == nil {
		t.Fatal("expected mismatch")
	}
}
func TestPythonCandidatesPrefersOverride(t *testing.T) {
	got := PythonCandidates(map[string]string{"FH6_PYTHON": "C:/custom/python.exe", "LOCALAPPDATA": "C:/Users/A/AppData/Local"})
	if len(got) == 0 || got[0] != "C:/custom/python.exe" {
		t.Fatalf("%v", got)
	}
}
func TestConfigureEmbeddedPythonAddsAbsoluteAppPath(t *testing.T) {
	d := t.TempDir()
	p := filepath.Join(d, "python313._pth")
	os.WriteFile(p, []byte("python313.zip\n.\n#import site\n"), 0644)
	app := filepath.Join(t.TempDir(), "app")
	if err := ConfigureEmbeddedPython(d, app); err != nil {
		t.Fatal(err)
	}
	b, _ := os.ReadFile(p)
	if !bytes.Contains(b, []byte(app)) {
		t.Fatalf("missing app path: %s", b)
	}
}

func TestPythonEmbedReleaseMetadataMatchesOfficialSBOM(t *testing.T) {
	const wantURL = "https://www.python.org/ftp/python/3.13.5/python-3.13.5-embed-amd64.zip"
	const wantSHA = "7d2650fd9d1b9d002d4a315d5f354247fd6a44f30517c7ef577b08f57a0fb6d9"
	if PythonURL != wantURL {
		t.Fatalf("PythonURL=%q want %q", PythonURL, wantURL)
	}
	if PythonSHA256 != wantSHA {
		t.Fatalf("PythonSHA256=%q want %q", PythonSHA256, wantSHA)
	}
}

func TestChoosePythonRuntimePrefersBundledEmbedOverSystemPython(t *testing.T) {
	if got := ChoosePythonRuntime(12_000_000, false, "C:/Python313/python.exe"); got != PythonRuntimeBundled {
		t.Fatalf("got %v; portable build must prefer bundled runtime", got)
	}
}
