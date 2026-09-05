package launcher_native

import (
	"os"
	"strings"
	"testing"
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
