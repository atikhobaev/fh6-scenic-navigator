package launcher_native

import (
	"encoding/json"
	"os"
	"path/filepath"
)

type Settings struct {
	AutoOpenDrive     bool   `json:"autoOpenDrive"`
	MinimizeAfterOpen bool   `json:"minimizeAfterOpen"`
	KeepRunningInTray bool   `json:"keepRunningInTray"`
	Locale            string `json:"locale"`
	HTTPPort          int    `json:"httpPort"`
	UDPPort           int    `json:"udpPort"`
}

func DefaultSettings() Settings { return Settings{true, false, false, "ru-RU", 8080, 1234} }
func LoadSettings(path string) Settings {
	s := DefaultSettings()
	b, e := os.ReadFile(path)
	if e == nil {
		_ = json.Unmarshal(b, &s)
	}
	if s.HTTPPort < 1 || s.HTTPPort > 65535 {
		s.HTTPPort = 8080
	}
	if s.UDPPort < 1 || s.UDPPort > 65535 {
		s.UDPPort = 1234
	}
	if s.Locale == "" {
		s.Locale = "ru-RU"
	}
	return s
}
func SaveSettings(path string, s Settings) error {
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		return err
	}
	b, err := json.MarshalIndent(s, "", "  ")
	if err != nil {
		return err
	}
	tmp := path + ".tmp"
	if err = os.WriteFile(tmp, b, 0644); err != nil {
		return err
	}
	return os.Rename(tmp, path)
}
