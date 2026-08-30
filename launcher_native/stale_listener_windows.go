//go:build windows

package launcher_native

import (
	"fmt"
	"os"
	"os/exec"
	"strings"
	"syscall"
	"time"
	"unsafe"
)

var pQueryFullProcessImageName = kernel32.NewProc("QueryFullProcessImageNameW")

func listenerPIDWindows(port int) (int, error) {
	cmd := exec.Command("netstat", "-ano", "-p", "tcp")
	configureHiddenProcess(cmd)
	out, err := cmd.Output()
	if err != nil {
		return 0, fmt.Errorf("netstat: %w", err)
	}
	return listenerPIDFromNetstat(string(out), port), nil
}

func processImagePathWindows(pid int) (string, error) {
	h, _, callErr := pOpenProcess.Call(processQueryLimitedInformation, 0, uintptr(uint32(pid)))
	if h == 0 {
		return "", fmt.Errorf("OpenProcess(%d): %v", pid, callErr)
	}
	defer pCloseHandle.Call(h)
	buf := make([]uint16, 32768)
	size := uint32(len(buf))
	r, _, callErr := pQueryFullProcessImageName.Call(h, 0, uintptr(unsafe.Pointer(&buf[0])), uintptr(unsafe.Pointer(&size)))
	if r == 0 {
		return "", fmt.Errorf("QueryFullProcessImageNameW(%d): %v", pid, callErr)
	}
	return syscall.UTF16ToString(buf[:size]), nil
}

func waitPortReleased(port int, timeout time.Duration) bool {
	deadline := time.Now().Add(timeout)
	base := fmt.Sprintf("http://127.0.0.1:%d", port)
	for time.Now().Before(deadline) {
		pid, _ := listenerPIDWindows(port)
		if pid == 0 {
			return true
		}
		// A health probe is intentionally best-effort; it also gives a short delay.
		_, _ = ProbeHealth(base)
		time.Sleep(100 * time.Millisecond)
	}
	pid, _ := listenerPIDWindows(port)
	return pid == 0
}

func cleanupStaleNavigator(port int, userRoot string, logf func(string)) error {
	pid, err := listenerPIDWindows(port)
	if err != nil || pid == 0 {
		return err
	}
	base := fmt.Sprintf("http://127.0.0.1:%d", port)
	info, _ := ProbeHealth(base)
	exePath, pathErr := processImagePathWindows(pid)
	if !mayTerminateStaleListener(info, exePath, userRoot) {
		if pathErr != nil {
			exePath = "unknown process"
		}
		return fmt.Errorf("HTTP port %d is used by another application (%s, PID %d)", port, strings.TrimSpace(exePath), pid)
	}
	if logf != nil {
		label := info.Version
		if label == "" {
			label = "stale managed runtime"
		}
		logf(fmt.Sprintf("Stopping previous FH6 Navigator (%s), PID %d", label, pid))
	}
	p, err := os.FindProcess(pid)
	if err != nil {
		return fmt.Errorf("find stale Navigator PID %d: %w", pid, err)
	}
	if err = p.Kill(); err != nil {
		return fmt.Errorf("stop stale Navigator PID %d: %w", pid, err)
	}
	if !waitPortReleased(port, 4*time.Second) {
		return fmt.Errorf("previous FH6 Navigator PID %d did not release port %d", pid, port)
	}
	if logf != nil {
		logf(fmt.Sprintf("Previous Navigator stopped; port %d is free", port))
	}
	return nil
}
