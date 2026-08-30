//go:build !windows

package launcher_native

func cleanupStaleNavigator(port int, userRoot string, logf func(string)) error { return nil }
