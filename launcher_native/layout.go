package launcher_native

func DefaultWindowLogicalSize() (int, int) { return 780, 650 }
func MinimumWindowLogicalSize() (int, int) { return 700, 560 }
func WindowLogicalHeight(logOpen bool) int {
	if logOpen {
		return 790
	}
	return 650
}
