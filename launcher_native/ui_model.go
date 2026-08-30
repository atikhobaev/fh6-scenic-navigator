package launcher_native

func PrimaryButtonLabel(m *Model) string {
	switch m.State {
	case Ready, Error:
		return "Запустить Navigator"
	case Running:
		return "Открыть DRIVE"
	default:
		return ""
	}
}
func SecondaryButtons(m *Model) []string {
	if m.State == Running {
		return []string{"Открыть PLAN", "Остановить"}
	}
	return nil
}
