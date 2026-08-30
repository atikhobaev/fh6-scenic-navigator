package launcher_native

import (
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"syscall"
	"testing"
	"time"
)

func TestWindowsLauncherLocksOSThreadBeforeFirstWin32Call(t *testing.T) {
	b, err := os.ReadFile("main_windows.go")
	if err != nil {
		t.Fatal(err)
	}
	src := string(b)
	lock := strings.Index(src, "runtime.LockOSThread()")
	firstWin32 := strings.Index(src, "pSetDpiContext.Call")
	if lock < 0 {
		t.Fatal("RunLauncher must lock its goroutine to the creating OS thread")
	}
	if firstWin32 < 0 {
		t.Fatal("expected Win32 initialization call")
	}
	if lock > firstWin32 {
		t.Fatal("runtime.LockOSThread must happen before any Win32 UI call")
	}
}

func TestLogsRemainReadableWhileDiskLogWriteIsBlocked(t *testing.T) {
	if runtime.GOOS != "linux" {
		t.Skip("FIFO-based regression probe")
	}
	dir := t.TempDir()
	fifo := filepath.Join(dir, "launcher.log")
	if err := syscall.Mkfifo(fifo, 0600); err != nil {
		t.Fatal(err)
	}

	c := &Controller{Model: NewModel(), logPath: fifo}
	done := make(chan struct{})
	go func() {
		c.addLog("first-start probe")
		close(done)
	}()

	// addLog appends to memory before opening the FIFO. Give it a moment to reach the blocked write.
	time.Sleep(50 * time.Millisecond)
	logsDone := make(chan []string, 1)
	go func() { logsDone <- c.Logs() }()

	select {
	case logs := <-logsDone:
		if len(logs) != 1 || !strings.Contains(logs[0], "first-start probe") {
			t.Fatalf("unexpected logs: %#v", logs)
		}
	case <-time.After(250 * time.Millisecond):
		// Unblock the writer before failing so the goroutine can exit cleanly.
		go func() {
			f, _ := os.OpenFile(fifo, os.O_RDONLY, 0600)
			if f != nil {
				_ = f.Close()
			}
		}()
		t.Fatal("Logs() blocked behind disk I/O mutex; WM_PAINT can become unresponsive")
	}

	// Unblock the FIFO writer and wait for addLog to finish.
	f, err := os.OpenFile(fifo, os.O_RDONLY, 0600)
	if err != nil {
		t.Fatal(err)
	}
	defer f.Close()
	select {
	case <-done:
	case <-time.After(time.Second):
		t.Fatal("addLog did not finish after FIFO reader opened")
	}
}

func TestCloseAlwaysShutsDownInsteadOfLeavingNavigatorOrphaned(t *testing.T) {
	b, err := os.ReadFile("main_windows.go")
	if err != nil {
		t.Fatal(err)
	}
	src := string(b)
	start := strings.Index(src, "case WM_CLOSE:")
	end := strings.Index(src[start:], "case WM_DESTROY:")
	if start < 0 || end < 0 {
		t.Fatal("WM_CLOSE handler not found")
	}
	block := src[start : start+end]
	if strings.Contains(block, "KeepRunningInTray") || strings.Contains(block, "SW_HIDE") {
		t.Fatal("closing the window must not leave Navigator running in tray")
	}
	if !strings.Contains(block, "StopAsync") {
		t.Fatal("WM_CLOSE must initiate non-blocking Navigator shutdown")
	}
	if !strings.Contains(block, "pDestroyWindow.Call") {
		t.Fatal("WM_CLOSE must destroy the window after scheduling shutdown")
	}
}

func TestWindowsChildLifetimeUsesKillOnJobClose(t *testing.T) {
	b, err := os.ReadFile("process_lifetime_windows.go")
	if err != nil {
		t.Fatal(err)
	}
	src := string(b)
	for _, required := range []string{
		"jobObjectLimitKillOnJobClose",
		"SetInformationJobObject",
		"AssignProcessToJobObject",
		"TerminateJobObject",
	} {
		if !strings.Contains(src, required) {
			t.Fatalf("missing Windows Job Object lifecycle primitive %q", required)
		}
	}
}
