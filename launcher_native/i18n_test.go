package launcher_native

import "testing"

func TestLauncherTranslationsCoverRuntimeAndTrayKeys(t *testing.T) {
	keys := []string{
		"stage_runtime", "stage_graph", "stage_localization", "stage_server",
		"fallback_names", "show_launcher", "exit", "lost", "errors",
		"stage_runtime_short", "stage_graph_short", "stage_localization_short", "stage_server_short",
	}
	for _, locale := range []string{"en-US", "zh-CN", "ru-RU", "es-419"} {
		for _, key := range keys {
			if got := T(locale, key); got == "" {
				t.Fatalf("missing %s translation for %s", key, locale)
			}
		}
	}
}
