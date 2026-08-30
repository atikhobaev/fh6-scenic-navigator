package launcher_native

import (
	"context"
	"os"
	"path/filepath"
	"runtime"
	"testing"
	"time"
)

func TestServerManagerCapturesEarlyExit(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("shell fixture")
	}
	d := t.TempDir()
	p := filepath.Join(d, "fail.sh")
	os.WriteFile(p, []byte("#!/bin/sh\necho boom\nexit 7\n"), 0755)
	var logs []string
	sm := NewServerManager(func(s string) { logs = append(logs, s) })
	err := sm.Start(context.Background(), p, nil, d)
	if err != nil {
		t.Fatal(err)
	}
	select {
	case e := <-sm.Exited():
		if e == nil {
			t.Fatal("expected exit error")
		}
	case <-time.After(2 * time.Second):
		t.Fatal("timeout")
	}
	if len(logs) == 0 {
		t.Fatal("missing logs")
	}
}
