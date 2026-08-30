package launcher_native

import (
	"bytes"
	"testing"
)

func TestEmbeddedLauncherIconIsPNG(t *testing.T) {
	if len(EmbeddedIconPNG) < 100 || !bytes.Equal(EmbeddedIconPNG[:8], []byte("\x89PNG\r\n\x1a\n")) {
		t.Fatal("launcher icon PNG missing or invalid")
	}
}
