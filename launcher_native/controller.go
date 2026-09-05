package launcher_native

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"sync"
	"time"
)

const AppVersion = "1.20.0"

type Controller struct {
	Model        *Model
	Settings     Settings
	settingsPath string
	server       *ServerManager
	cancel       context.CancelFunc
	mu           sync.Mutex
	logs         []string
	logPath      string
	onChange     func()
	appDir       string
	userRoot     string
	baseURL      string
}

func NewController(onChange func()) *Controller {
	root := RuntimeRoot()
	settingsPath := filepath.Join(root, "settings.json")
	c := &Controller{Model: NewModel(), Settings: LoadSettings(settingsPath), settingsPath: settingsPath, onChange: onChange, userRoot: root, logPath: filepath.Join(root, "logs", "launcher.log")}
	c.server = NewServerManager(c.serverLog)
	return c
}
func (c *Controller) notify() {
	if c.onChange != nil {
		c.onChange()
	}
}
func (c *Controller) addLog(line string) {
	line = strings.TrimSpace(line)
	if line == "" {
		return
	}
	stamp := time.Now().Format("15:04:05")
	row := stamp + "  " + line
	c.mu.Lock()
	c.logs = append(c.logs, row)
	if len(c.logs) > 300 {
		c.logs = append([]string(nil), c.logs[len(c.logs)-300:]...)
	}
	c.mu.Unlock()

	// Publish the in-memory snapshot before touching disk. The Win32 paint path
	// reads Logs(), so it must never wait behind slow antivirus/filesystem I/O.
	c.notify()
	os.MkdirAll(filepath.Dir(c.logPath), 0755)
	f, _ := os.OpenFile(c.logPath, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0644)
	if f != nil {
		fmt.Fprintln(f, row)
		f.Close()
	}
}
func (c *Controller) serverLog(line string) {
	c.addLog(line)
	switch {
	case strings.Contains(line, "[2/4]"):
		c.Model.SetStarting(StageGraph, T(c.Settings.Locale, "stage_graph"))
	case strings.Contains(line, "[3/4]"):
		c.Model.SetStarting(StageLocalization, T(c.Settings.Locale, "stage_localization"))
	case strings.Contains(line, "[4/4]") || strings.Contains(line, "[server"):
		c.Model.SetStarting(StageServer, T(c.Settings.Locale, "stage_server"))
	default:
		return
	}
	c.notify()
}

func (c *Controller) Logs() []string {
	c.mu.Lock()
	defer c.mu.Unlock()
	return append([]string(nil), c.logs...)
}
func (c *Controller) LogPath() string  { return c.logPath }
func (c *Controller) UserRoot() string { return c.userRoot }
func (c *Controller) SaveSettings()    { _ = SaveSettings(c.settingsPath, c.Settings) }

func (c *Controller) Start() {
	if c.server.Running() || c.Model.State == Starting {
		return
	}
	ctx, cancel := context.WithCancel(context.Background())
	c.cancel = cancel
	go c.start(ctx)
}
func (c *Controller) start(ctx context.Context) {
	c.Model.SetStarting(StageRuntime, T(c.Settings.Locale, "stage_runtime"))
	c.notify()
	c.addLog("Preparing portable runtime")
	if err := cleanupStaleNavigator(c.Settings.HTTPPort, c.userRoot, c.addLog); err != nil {
		c.fail("Не удалось освободить HTTP порт", err)
		return
	}
	versionRoot := filepath.Join(c.userRoot, "runtime", AppVersion)
	appDir := filepath.Join(versionRoot, "app")
	if err := ExtractPayload(EmbeddedAppPayload, appDir, AppVersion); err != nil {
		c.fail("Не удалось распаковать Navigator", err)
		return
	}
	c.appDir = appDir
	var systemPy string
	systemPy, _ = ResolvePython(envMap())
	embeddedPyDir := filepath.Join(versionRoot, "python")
	zipPath := filepath.Join(c.userRoot, "runtime", "python-3.13.5-embed-amd64.zip")
	_, cachedErr := os.Stat(zipPath)
	choice := ChoosePythonRuntime(len(EmbeddedPythonZip), cachedErr == nil, systemPy)
	py := systemPy
	var err error
	if choice != PythonRuntimeSystem {
		py = filepath.Join(embeddedPyDir, "python.exe")
		if _, e := os.Stat(py); e != nil {
			switch choice {
			case PythonRuntimeBundled:
				c.addLog("Preparing bundled CPython 3.13.5 runtime")
				if err = os.MkdirAll(filepath.Dir(zipPath), 0755); err == nil {
					err = os.WriteFile(zipPath, EmbeddedPythonZip, 0644)
				}
				if err == nil {
					err = VerifySHA256(zipPath, PythonSHA256)
				}
			case PythonRuntimeCached:
				c.addLog("Using cached verified CPython 3.13.5 runtime")
				err = VerifySHA256(zipPath, PythonSHA256)
			case PythonRuntimeDownload:
				c.addLog("Downloading official CPython 3.13.5 runtime")
				err = DownloadPythonEmbed(zipPath, func(n, total int64) {
					if total > 0 {
						c.Model.SetRuntimeProgress(int(n * 100 / total))
						c.notify()
					}
				})
			}
			if err != nil {
				c.fail("Не удалось подготовить Python runtime", err)
				return
			}
			if err = ExtractPythonEmbed(zipPath, embeddedPyDir); err != nil {
				c.fail("Не удалось распаковать Python runtime", err)
				return
			}
		}
		if err = ConfigureEmbeddedPython(embeddedPyDir, appDir); err != nil {
			c.fail("Не удалось настроить Python runtime", err)
			return
		}
	} else {
		c.addLog("Using system Python runtime")
	}
	c.Model.SetStarting(StageGraph, T(c.Settings.Locale, "stage_graph"))
	c.notify()
	env := os.Environ()
	env = append(env, "FH6_NATIVE_LAUNCHER=1", "FH6_HTTP_PORT="+strconv.Itoa(c.Settings.HTTPPort), "FH6_UDP_PORT="+strconv.Itoa(c.Settings.UDPPort), "FH6_USER_DATA_DIR="+c.userRoot, "PYTHONUTF8=1", "PYTHONUNBUFFERED=1")
	if err = c.server.StartEnv(ctx, py, []string{"launcher.py"}, appDir, env); err != nil {
		c.fail("Не удалось запустить сервер", err)
		return
	}
	base := fmt.Sprintf("http://127.0.0.1:%d", c.Settings.HTTPPort)
	c.baseURL = base
	deadline := time.Now().Add(45 * time.Second)
	for time.Now().Before(deadline) {
		select {
		case <-ctx.Done():
			return
		case exitErr := <-c.server.Exited():
			c.fail("Сервер завершился во время запуска", exitErr)
			return
		case <-time.After(250 * time.Millisecond):
		}
		h, e := ProbeHealth(base)
		if e == nil && h.Name == "FH6 Scenic Navigator" {
			lan := fmt.Sprintf("http://%s:%d", h.LANIP, h.HTTPPort)
			c.Model.SetRunning(base, lan)
			c.loadStatusMeta()
			c.notify()
			c.addLog("Navigator ready at " + base)
			if c.Settings.AutoOpenDrive {
				OpenURL(base + "?lang=" + c.Settings.Locale)
			}
			go c.monitor(ctx)
			return
		}
	}
	c.server.Stop()
	c.fail("Navigator не успел запуститься", fmt.Errorf("health check timeout"))
}
func (c *Controller) loadStatusMeta() {
	fh6Found := false
	localization := ""
	places := 0
	p := filepath.Join(c.appDir, "static", "data", "place_names_meta.json")
	if b, e := os.ReadFile(p); e == nil {
		var v struct {
			Status   string `json:"status"`
			Coverage map[string]struct {
				Matched int `json:"matched"`
				Total   int `json:"total"`
			} `json:"coverage"`
		}
		if json.Unmarshal(b, &v) == nil {
			fh6Found = v.Status == "ready"
			if row, ok := v.Coverage[c.Settings.Locale]; ok {
				localization = fmt.Sprintf("%d / %d", row.Matched, row.Total)
			}
		}
	}
	for _, name := range []string{"builtin_places.json", "scenic_catalog.json", "community_places.json"} {
		b, e := os.ReadFile(filepath.Join(c.appDir, "static", "data", name))
		if e != nil {
			continue
		}
		var d struct {
			Places []json.RawMessage `json:"places"`
		}
		if json.Unmarshal(b, &d) == nil {
			places += len(d.Places)
		}
	}
	c.Model.SetCatalogStatus(fh6Found, localization, places)
}
func (c *Controller) monitor(ctx context.Context) {
	tick := time.NewTicker(time.Second)
	defer tick.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-tick.C:
			t, e := ProbeTelemetry(c.baseURL)
			if e == nil {
				c.Model.SetTelemetry(t.Connected)
				c.notify()
			}
			if !c.server.Running() {
				c.Model.SetError("Сервер остановлен")
				c.notify()
				return
			}
		}
	}
}
func (c *Controller) fail(msg string, err error) {
	if err != nil {
		c.addLog("ERROR: " + err.Error())
	}
	c.Model.SetError(msg)
	c.notify()
}
func (c *Controller) StopAsync() {
	snap := c.Model.Snapshot()
	if snap.State == Ready || snap.State == Stopping {
		return
	}
	if c.cancel != nil {
		c.cancel()
	}
	c.Model.SetStopping()
	c.notify()
	go func() {
		_ = c.server.Stop()
		c.Model.SetReady()
		c.notify()
		c.addLog("Navigator stopped")
	}()
}

func (c *Controller) Stop() {
	c.StopAsync()
	deadline := time.Now().Add(3 * time.Second)
	for c.Model.Snapshot().State == Stopping && time.Now().Before(deadline) {
		time.Sleep(10 * time.Millisecond)
	}
}
func (c *Controller) OpenDrive() {
	if c.baseURL != "" {
		OpenURL(c.baseURL + "?lang=" + c.Settings.Locale)
	}
}
func (c *Controller) OpenPlan() {
	if c.baseURL != "" {
		OpenURL(c.baseURL + "/planner/?lang=" + c.Settings.Locale)
	}
}
func envMap() map[string]string {
	m := map[string]string{}
	for _, kv := range os.Environ() {
		if i := strings.IndexByte(kv, '='); i > 0 {
			m[kv[:i]] = kv[i+1:]
		}
	}
	return m
}

var _ = runtime.GOOS
