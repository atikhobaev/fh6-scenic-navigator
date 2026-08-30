package launcher_native

import "sync"

type AppState int

const (
	Ready AppState = iota
	Starting
	Running
	Error
	Stopping
)

type StartupStage int

const (
	StageIdle StartupStage = iota
	StageRuntime
	StageGraph
	StageLocalization
	StageServer
	StageReady
)

type Actions struct{ Start, OpenDrive, OpenPlan, Stop, Retry bool }
type Model struct {
	mu                                sync.RWMutex
	State                             AppState
	Stage                             StartupStage
	Title, Subtitle, LocalURL, LANURL string
	Actions                           Actions
	LogExpanded                       bool
	TelemetryConnected                bool
	TelemetrySeen                     bool
	ProgressPercent                   int
	Localization                      string
	Places                            int
	FH6Found                          bool
}

func NewModel() *Model { m := &Model{}; m.SetReady(); return m }
func (m *Model) SetReady() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.State = Ready
	m.Stage = StageIdle
	m.Title = "Готов к запуску"
	m.Subtitle = "Все необходимые данные будут проверены автоматически"
	m.Actions = Actions{Start: true}
	m.LogExpanded = false
	m.ProgressPercent = -1
	m.TelemetryConnected = false
	m.TelemetrySeen = false
}
func (m *Model) SetStarting(stage StartupStage, msg string) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.State = Starting
	m.Stage = stage
	m.Title = "Запуск Navigator"
	m.Subtitle = msg
	m.Actions = Actions{}
	m.ProgressPercent = -1
}
func (m *Model) SetRunning(local, lan string) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.State = Running
	m.Stage = StageReady
	m.Title = "Navigator работает"
	m.Subtitle = "Сервер готов · ожидаю телеметрию FH6"
	m.LocalURL = local
	m.LANURL = lan
	m.Actions = Actions{OpenDrive: true, OpenPlan: true, Stop: true}
	m.ProgressPercent = -1
	m.TelemetryConnected = false
	m.TelemetrySeen = false
}
func (m *Model) SetError(msg string) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.State = Error
	m.Title = "Не удалось запустить Navigator"
	m.Subtitle = msg
	m.Actions = Actions{Retry: true}
	m.LogExpanded = true
}
func (m *Model) SetStopping() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.State = Stopping
	m.Title = "Остановка Navigator"
	m.Subtitle = "Завершаю локальный сервер…"
	m.Actions = Actions{}
}

func (m *Model) Snapshot() Model {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return Model{State: m.State, Stage: m.Stage, Title: m.Title, Subtitle: m.Subtitle, LocalURL: m.LocalURL, LANURL: m.LANURL, Actions: m.Actions, LogExpanded: m.LogExpanded, TelemetryConnected: m.TelemetryConnected, TelemetrySeen: m.TelemetrySeen, ProgressPercent: m.ProgressPercent, Localization: m.Localization, Places: m.Places, FH6Found: m.FH6Found}
}

func (m *Model) SetRuntimeSubtitle(text string) { m.mu.Lock(); defer m.mu.Unlock(); m.Subtitle = text }
func (m *Model) SetRuntimeProgress(percent int) {
	m.mu.Lock()
	defer m.mu.Unlock()
	if percent < 0 {
		percent = 0
	}
	if percent > 100 {
		percent = 100
	}
	m.Stage = StageRuntime
	m.ProgressPercent = percent
}
func (m *Model) SetTelemetry(connected bool) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.TelemetryConnected = connected
	if connected {
		m.TelemetrySeen = true
	}
}
func (m *Model) SetCatalogStatus(fh6 bool, localization string, places int) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.FH6Found = fh6
	m.Localization = localization
	m.Places = places
}
