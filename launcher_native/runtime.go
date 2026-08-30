package launcher_native

import (
	"archive/zip"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"
)

const PythonURL = "https://www.python.org/ftp/python/3.13.5/python-3.13.5-embed-amd64.zip"
const PythonSHA256 = "7d2650fd9d1b9d002d4a315d5f354247fd6a44f30517c7ef577b08f57a0fb6d9"

type PythonRuntimeChoice int

const (
	PythonRuntimeBundled PythonRuntimeChoice = iota
	PythonRuntimeCached
	PythonRuntimeSystem
	PythonRuntimeDownload
)

func ChoosePythonRuntime(embeddedLen int, cachedEmbed bool, systemPath string) PythonRuntimeChoice {
	if embeddedLen > 1024 {
		return PythonRuntimeBundled
	}
	if cachedEmbed {
		return PythonRuntimeCached
	}
	if strings.TrimSpace(systemPath) != "" {
		return PythonRuntimeSystem
	}
	return PythonRuntimeDownload
}

func PythonCandidates(env map[string]string) []string {
	var out []string
	if p := strings.TrimSpace(env["FH6_PYTHON"]); p != "" {
		out = append(out, p)
	}
	if la := env["LOCALAPPDATA"]; la != "" {
		for _, v := range []string{"Python313", "Python312", "Python311"} {
			out = append(out, filepath.Join(la, "Programs", "Python", v, "python.exe"))
		}
	}
	out = append(out, "py.exe", "python.exe")
	return out
}
func ResolvePython(env map[string]string) (string, error) {
	for _, p := range PythonCandidates(env) {
		if strings.ContainsRune(p, filepath.Separator) || strings.Contains(p, "/") {
			if st, e := os.Stat(p); e == nil && !st.IsDir() {
				return p, nil
			}
			continue
		}
		if q, e := exec.LookPath(p); e == nil {
			return q, nil
		}
	}
	return "", fmt.Errorf("Python 3.11+ not found")
}
func VerifySHA256(path, want string) error {
	f, e := os.Open(path)
	if e != nil {
		return e
	}
	defer f.Close()
	h := sha256.New()
	if _, e = io.Copy(h, f); e != nil {
		return e
	}
	got := hex.EncodeToString(h.Sum(nil))
	if !strings.EqualFold(got, want) {
		return fmt.Errorf("SHA-256 mismatch: got %s", got)
	}
	return nil
}
func DownloadPythonEmbed(dst string, progress func(int64, int64)) error {
	c := &http.Client{Timeout: 5 * time.Minute}
	r, e := c.Get(PythonURL)
	if e != nil {
		return e
	}
	defer r.Body.Close()
	if r.StatusCode != http.StatusOK {
		return fmt.Errorf("python.org HTTP %d", r.StatusCode)
	}
	if e = os.MkdirAll(filepath.Dir(dst), 0755); e != nil {
		return e
	}
	tmp := dst + ".part"
	f, e := os.Create(tmp)
	if e != nil {
		return e
	}
	var n int64
	buf := make([]byte, 256*1024)
	total := r.ContentLength
	for {
		m, er := r.Body.Read(buf)
		if m > 0 {
			if _, e = f.Write(buf[:m]); e != nil {
				f.Close()
				return e
			}
			n += int64(m)
			if progress != nil {
				progress(n, total)
			}
		}
		if er == io.EOF {
			break
		}
		if er != nil {
			f.Close()
			return er
		}
	}
	f.Close()
	if e = VerifySHA256(tmp, PythonSHA256); e != nil {
		os.Remove(tmp)
		return e
	}
	return os.Rename(tmp, dst)
}
func ExtractPythonEmbed(zipPath, dir string) error {
	os.RemoveAll(dir)
	os.MkdirAll(dir, 0755)
	z, e := zip.OpenReader(zipPath)
	if e != nil {
		return e
	}
	defer z.Close()
	for _, f := range z.File {
		dst := filepath.Join(dir, filepath.Clean(f.Name))
		if !strings.HasPrefix(dst, filepath.Clean(dir)+string(os.PathSeparator)) {
			return fmt.Errorf("unsafe python path")
		}
		if f.FileInfo().IsDir() {
			os.MkdirAll(dst, 0755)
			continue
		}
		os.MkdirAll(filepath.Dir(dst), 0755)
		rc, e := f.Open()
		if e != nil {
			return e
		}
		o, e := os.Create(dst)
		if e == nil {
			_, e = io.Copy(o, rc)
		}
		o.Close()
		rc.Close()
		if e != nil {
			return e
		}
	}
	return nil
}
func ConfigureEmbeddedPython(dir, appDir string) error {
	files, _ := filepath.Glob(filepath.Join(dir, "python*._pth"))
	if len(files) == 0 {
		return fmt.Errorf("embedded Python _pth file not found")
	}
	for _, p := range files {
		b, e := os.ReadFile(p)
		if e != nil {
			return e
		}
		s := strings.ReplaceAll(string(b), "#import site", "import site")
		if !strings.Contains(s, appDir) {
			s += "\n" + appDir + "\n"
		}
		if e = os.WriteFile(p, []byte(s), 0644); e != nil {
			return e
		}
	}
	return nil
}
func RuntimeRoot() string {
	if runtime.GOOS != "windows" {
		return filepath.Join(os.TempDir(), "FH6 Scenic Navigator")
	}
	base := os.Getenv("LOCALAPPDATA")
	if base == "" {
		base = os.TempDir()
	}
	return filepath.Join(base, "FH6 Scenic Navigator")
}
