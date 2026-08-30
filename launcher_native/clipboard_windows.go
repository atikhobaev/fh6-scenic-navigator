//go:build windows

package launcher_native

import (
	"os/exec"
	"strings"
)

func CopyText(text string) {
	cmd := exec.Command("cmd.exe", "/c", "clip")
	configureHiddenProcess(cmd)
	cmd.Stdin = strings.NewReader(text)
	_ = cmd.Run()
}
func OpenFolder(path string) { OpenURL(path) }
