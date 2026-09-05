package launcher_native

import (
	"os"
	"path/filepath"
	"strings"
	"syscall"
	"testing"
	"time"
)

func TestLogsRemainReadableWhileDiskLogWriteIsBlocked(t *testing.T) {
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
