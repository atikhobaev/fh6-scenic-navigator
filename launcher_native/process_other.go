//go:build !windows

package launcher_native

import "os/exec"

func configureHiddenProcess(cmd *exec.Cmd) {}
