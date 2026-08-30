package launcher_native

import "testing"

func TestStateActionSets(t *testing.T) {
	m := NewModel()
	if m.State != Ready || !m.Actions.Start || m.Actions.OpenDrive {
		t.Fatalf("ready actions: %+v", m)
	}
	m.SetStarting(StageServer, "Starting server")
	if m.State != Starting || m.Actions.Start || m.Actions.OpenDrive {
		t.Fatalf("starting actions: %+v", m)
	}
	m.SetRunning("127.0.0.1:8080", "192.168.1.2:8080")
	if m.State != Running || !m.Actions.OpenDrive || !m.Actions.OpenPlan || !m.Actions.Stop {
		t.Fatalf("running actions: %+v", m)
	}
	m.SetError("port conflict")
	if m.State != Error || !m.Actions.Retry || !m.LogExpanded {
		t.Fatalf("error actions: %+v", m)
	}
}

func TestDefaultSettings(t *testing.T) {
	s := DefaultSettings()
	if !s.AutoOpenDrive || s.MinimizeAfterOpen || s.KeepRunningInTray || s.Locale != "ru-RU" || s.HTTPPort != 8080 || s.UDPPort != 1234 {
		t.Fatalf("defaults: %+v", s)
	}
}

func TestStatusTextUsesLocalizedStageAndRuntimeProgress(t *testing.T) {
	m := NewModel()
	m.SetStarting(StageRuntime, "")
	m.SetRuntimeProgress(42)
	_, sub := StatusText(m, "en-US")
	if sub != "Preparing portable runtime · 42%" {
		t.Fatalf("subtitle=%q", sub)
	}
	_, sub = StatusText(m, "ru-RU")
	if sub != "Подготовка встроенного runtime · 42%" {
		t.Fatalf("ru subtitle=%q", sub)
	}
}

func TestTelemetryDistinguishesWaitingConnectedAndLost(t *testing.T) {
	m := NewModel()
	m.SetRunning("http://127.0.0.1:8080", "http://192.168.1.2:8080")
	_, sub := StatusText(m, "ru-RU")
	if sub != T("ru-RU", "waiting") {
		t.Fatalf("waiting=%q", sub)
	}
	m.SetTelemetry(true)
	_, sub = StatusText(m, "ru-RU")
	if sub != T("ru-RU", "connected") {
		t.Fatalf("connected=%q", sub)
	}
	m.SetTelemetry(false)
	_, sub = StatusText(m, "ru-RU")
	if sub != T("ru-RU", "lost") {
		t.Fatalf("lost=%q", sub)
	}
}
