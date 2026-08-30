package launcher_native

import (
	"strconv"
	"strings"
)

func listenerPIDFromNetstat(text string, port int) int {
	wanted := strconv.Itoa(port)
	for _, raw := range strings.Split(text, "\n") {
		parts := strings.Fields(raw)
		if len(parts) < 5 || !strings.EqualFold(parts[0], "TCP") {
			continue
		}
		local := parts[1]
		state := parts[len(parts)-2]
		pidText := parts[len(parts)-1]
		if !strings.HasPrefix(strings.ToUpper(state), "LISTEN") {
			continue
		}
		idx := strings.LastIndex(local, ":")
		if idx < 0 || local[idx+1:] != wanted {
			continue
		}
		pid, err := strconv.Atoi(pidText)
		if err == nil && pid > 0 {
			return pid
		}
	}
	return 0
}

func mayTerminateStaleListener(info Health, exePath, userRoot string) bool {
	if info.Name == "FH6 Scenic Navigator" {
		return true
	}
	return isManagedNavigatorExecutable(exePath, userRoot)
}
