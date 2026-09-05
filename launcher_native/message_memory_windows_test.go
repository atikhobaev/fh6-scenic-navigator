//go:build windows

package launcher_native

import (
	"testing"
	"unsafe"
)

func TestNativeMessageMemoryCopyPreservesRect(t *testing.T) {
	source := RECT{Left: 12, Top: 34, Right: 800, Bottom: 600}
	var target RECT
	pCopyMemory.Call(uintptr(unsafe.Pointer(&target)), uintptr(unsafe.Pointer(&source)), unsafe.Sizeof(source))
	if target != source {
		t.Fatalf("message rectangle changed: %#v", target)
	}
}
