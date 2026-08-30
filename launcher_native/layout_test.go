package launcher_native

import "testing"

func TestLauncherLogicalSizing(t *testing.T) {
	w, h := DefaultWindowLogicalSize()
	if w != 780 || h != 650 {
		t.Fatalf("default=%dx%d", w, h)
	}
	mw, mh := MinimumWindowLogicalSize()
	if mw != 700 || mh != 560 {
		t.Fatalf("minimum=%dx%d", mw, mh)
	}
	if WindowLogicalHeight(true) <= WindowLogicalHeight(false) {
		t.Fatal("expanded log must increase height")
	}
}
