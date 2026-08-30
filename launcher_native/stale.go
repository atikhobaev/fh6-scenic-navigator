package launcher_native

import (
	"path"
	"path/filepath"
	"strings"
)

func normalizeManagedPath(value string) string {
	value = strings.ReplaceAll(value, "\\", "/")
	value = filepath.ToSlash(filepath.Clean(value))
	return strings.ToLower(strings.TrimRight(value, "/"))
}

func isManagedNavigatorExecutable(exePath, userRoot string) bool {
	exe := normalizeManagedPath(exePath)
	root := normalizeManagedPath(userRoot)
	if exe == "" || root == "" {
		return false
	}
	base := strings.ToLower(path.Base(exe))
	if base != "python.exe" && base != "pythonw.exe" {
		return false
	}
	return strings.HasPrefix(exe, root+"/runtime/")
}
