package launcher_native

import "fmt"

func StatusText(m *Model, locale string) (string, string) {
	switch m.State {
	case Ready:
		return T(locale, "ready"), T(locale, "ready_sub")
	case Starting:
		key := "stage_runtime"
		switch m.Stage {
		case StageGraph:
			key = "stage_graph"
		case StageLocalization:
			key = "stage_localization"
		case StageServer:
			key = "stage_server"
		}
		sub := T(locale, key)
		if m.Stage == StageRuntime && m.ProgressPercent >= 0 {
			sub = fmt.Sprintf("%s · %d%%", sub, m.ProgressPercent)
		}
		return T(locale, "starting"), sub
	case Running:
		if m.TelemetryConnected {
			return T(locale, "running"), T(locale, "connected")
		}
		if m.TelemetrySeen {
			return T(locale, "running"), T(locale, "lost")
		}
		return T(locale, "running"), T(locale, "waiting")
	case Error:
		return T(locale, "error"), m.Subtitle
	case Stopping:
		return T(locale, "stop"), m.Subtitle
	}
	return "", ""
}
