//go:build windows

package launcher_native

import (
	"syscall"
	"unsafe"
)

var shell32 = syscall.NewLazyDLL("shell32.dll")
var procShellExecute = shell32.NewProc("ShellExecuteW")

func OpenURL(url string) {
	u, _ := syscall.UTF16PtrFromString(url)
	verb, _ := syscall.UTF16PtrFromString("open")
	procShellExecute.Call(0, uintptr(unsafe.Pointer(verb)), uintptr(unsafe.Pointer(u)), 0, 0, 1)
}
