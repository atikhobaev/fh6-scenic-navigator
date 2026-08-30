package launcher_native

import (
	"context"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
	"time"
)

type fakeLifetime struct {
	assigned   int
	terminated bool
	closed     bool
}

func (f *fakeLifetime) Assign(pid int) error { f.assigned = pid; return nil }
func (f *fakeLifetime) Terminate() error {
	f.terminated = true
	if f.assigned > 0 {
		if p, err := os.FindProcess(f.assigned); err == nil {
			_ = p.Kill()
		}
	}
	return nil
}
func (f *fakeLifetime) Close() error { f.closed = true; return nil }

func TestServerManagerOwnsChildLifetimeAndTerminatesGroup(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("portable shell fixture")
	}
	dir := t.TempDir()
	script := filepath.Join(dir, "wait.sh")
	if err := os.WriteFile(script, []byte("#!/bin/sh\nsleep 30\n"), 0755); err != nil {
		t.Fatal(err)
	}
	guard := &fakeLifetime{}
	sm := NewServerManagerWithLifetime(nil, func() (processLifetime, error) { return guard, nil })
	if err := sm.Start(context.Background(), script, nil, dir); err != nil {
		t.Fatal(err)
	}
	if guard.assigned <= 0 {
		t.Fatal("child was not assigned to process lifetime guard")
	}
	if err := sm.Stop(); err != nil {
		t.Fatal(err)
	}
	deadline := time.Now().Add(2 * time.Second)
	for sm.Running() && time.Now().Before(deadline) {
		time.Sleep(10 * time.Millisecond)
	}
	if !guard.terminated {
		t.Fatal("Stop must terminate the owned process group")
	}
	if !guard.closed {
		t.Fatal("Stop must close the process lifetime guard")
	}
}

func TestManagedRuntimePathIsSafeToCleanAsStaleNavigator(t *testing.T) {
	root := filepath.Clean(`C:\Users\A\AppData\Local\FH6 Scenic Navigator`)
	good := filepath.Join(root, "runtime", "1.19.2", "python", "python.exe")
	if !isManagedNavigatorExecutable(good, root) {
		t.Fatalf("expected managed runtime path: %s", good)
	}
	if isManagedNavigatorExecutable(`C:\Python313\python.exe`, root) {
		t.Fatal("system Python must never be killed merely because it uses port 8080")
	}
	if isManagedNavigatorExecutable(filepath.Join(root, "logs", "python.exe"), root) {
		t.Fatal("only runtime subtree is managed")
	}
}

func TestListenerPIDFromNetstatFindsRequestedPort(t *testing.T) {
	text := "  TCP    0.0.0.0:8080     0.0.0.0:0      LISTENING       4242\r\n" +
		"  TCP    127.0.0.1:9000   0.0.0.0:0      LISTENING       9001\r\n"
	if got := listenerPIDFromNetstat(text, 8080); got != 4242 {
		t.Fatalf("got %d", got)
	}
	if got := listenerPIDFromNetstat(text, 7000); got != 0 {
		t.Fatalf("unexpected pid %d", got)
	}
}

func TestStaleListenerCleanupRequiresNavigatorIdentityOrManagedRuntimePath(t *testing.T) {
	root := `C:\Users\A\AppData\Local\FH6 Scenic Navigator`
	managed := root + `\runtime\1.19.2\python\python.exe`
	if !mayTerminateStaleListener(Health{Name: "FH6 Scenic Navigator"}, `C:\Python313\python.exe`, root) {
		t.Fatal("a responding FH6 Navigator is safe to stop even if an older build used system Python")
	}
	if !mayTerminateStaleListener(Health{}, managed, root) {
		t.Fatal("an unresponsive listener inside our managed runtime is safe to clean")
	}
	if mayTerminateStaleListener(Health{}, `C:\Python313\python.exe`, root) {
		t.Fatal("an unknown application/system Python must never be terminated")
	}
}

func TestControllerCleansManagedStaleListenerBeforeStartingServer(t *testing.T) {
	b, err := os.ReadFile("controller.go")
	if err != nil {
		t.Fatal(err)
	}
	src := string(b)
	cleanup := strings.Index(src, "cleanupStaleNavigator(c.Settings.HTTPPort")
	start := strings.Index(src, "c.server.StartEnv")
	if cleanup < 0 {
		t.Fatal("controller must clean stale managed listener before starting Python")
	}
	if start < 0 {
		t.Fatal("server start call not found")
	}
	if cleanup > start {
		t.Fatal("stale listener cleanup must happen before server start")
	}
}
