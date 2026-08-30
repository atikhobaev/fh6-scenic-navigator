package launcher_native

import (
	"archive/zip"
	"bytes"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
)

func ExtractPayload(data []byte, dir, version string) error {
	marker := filepath.Join(dir, ".payload-version")
	if b, e := os.ReadFile(marker); e == nil && string(b) == version {
		if _, e := os.Stat(filepath.Join(dir, "server.py")); e == nil {
			return nil
		}
	}
	os.RemoveAll(dir)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return err
	}
	zr, err := zip.NewReader(bytes.NewReader(data), int64(len(data)))
	if err != nil {
		return err
	}
	for _, f := range zr.File {
		name := filepath.Clean(f.Name)
		if strings.HasPrefix(name, "..") || filepath.IsAbs(name) {
			return fmt.Errorf("unsafe payload path %q", f.Name)
		}
		dst := filepath.Join(dir, name)
		if f.FileInfo().IsDir() {
			os.MkdirAll(dst, 0755)
			continue
		}
		if err := os.MkdirAll(filepath.Dir(dst), 0755); err != nil {
			return err
		}
		rc, e := f.Open()
		if e != nil {
			return e
		}
		out, e := os.Create(dst)
		if e == nil {
			_, e = io.Copy(out, rc)
		}
		out.Close()
		rc.Close()
		if e != nil {
			return e
		}
	}
	return os.WriteFile(marker, []byte(version), 0644)
}
