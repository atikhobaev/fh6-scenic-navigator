package launcher_native

import "testing"

func TestPrimaryTextChangesByState(t *testing.T) {
	m := NewModel()
	if PrimaryButtonLabel(m) != "Запустить Navigator" {
		t.Fatal(PrimaryButtonLabel(m))
	}
	m.SetStarting(StageRuntime, "x")
	if PrimaryButtonLabel(m) != "" {
		t.Fatal(PrimaryButtonLabel(m))
	}
	m.SetRunning("a", "b")
	if PrimaryButtonLabel(m) != "Открыть DRIVE" {
		t.Fatal(PrimaryButtonLabel(m))
	}
}
