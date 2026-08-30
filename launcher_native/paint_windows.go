//go:build windows

package launcher_native

import (
	"fmt"
	"strings"
	"syscall"
	"unsafe"
)

type hitID int

const (
	hitNone hitID = iota
	hitStart
	hitDrive
	hitPlan
	hitStop
	hitSettings
	hitLog
	hitCopyLog
	hitOpenLogs
	hitAutoDrive
	hitMinimize
	hitTray
	hitLocale
	hitDone
)

type hitRegion struct {
	id hitID
	r  RECT
}
type nativeWindow struct {
	hwnd          syscall.Handle
	controller    *Controller
	hits          []hitRegion
	settingsOpen  bool
	logOpen       bool
	hover         hitID
	trayAdded     bool
	autoMinimized bool
}

func scaleRect(r RECT, s float64) RECT {
	return RECT{int32(float64(r.Left) * s), int32(float64(r.Top) * s), int32(float64(r.Right) * s), int32(float64(r.Bottom) * s)}
}
func color(hex uint32) uintptr { return rgb(byte(hex>>16), byte(hex>>8), byte(hex)) }
func fillRound(hdc syscall.Handle, r RECT, radius int32, hex uint32) {
	b, _, _ := pCreateSolidBrush.Call(color(hex))
	oldb, _, _ := pSelectObject.Call(uintptr(hdc), b)
	pen, _, _ := pGetStockObject.Call(NULL_PEN)
	oldp, _, _ := pSelectObject.Call(uintptr(hdc), pen)
	pRoundRect.Call(uintptr(hdc), uintptr(r.Left), uintptr(r.Top), uintptr(r.Right), uintptr(r.Bottom), uintptr(radius), uintptr(radius))
	pSelectObject.Call(uintptr(hdc), oldp)
	pSelectObject.Call(uintptr(hdc), oldb)
	pDeleteObject.Call(b)
}
func outlineRound(hdc syscall.Handle, r RECT, radius int32, border, fill uint32) {
	fillRound(hdc, r, radius, border)
	inner := RECT{r.Left + 1, r.Top + 1, r.Right - 1, r.Bottom - 1}
	fillRound(hdc, inner, radius-1, fill)
}
func drawText(hdc syscall.Handle, text string, r RECT, size int, weight int, hex uint32, flags uint32) {
	face := u16("Segoe UI Variable Text")
	font, _, _ := pCreateFont.Call(uintptr(int32(-size)), 0, 0, 0, uintptr(weight), 0, 0, 0, 1, 0, 0, 5, 0, uintptr(unsafe.Pointer(face)))
	old, _, _ := pSelectObject.Call(uintptr(hdc), font)
	pSetBkMode.Call(uintptr(hdc), TRANSPARENT)
	pSetTextColor.Call(uintptr(hdc), color(hex))
	u := syscall.StringToUTF16(text)
	if len(u) > 0 {
		pDrawText.Call(uintptr(hdc), uintptr(unsafe.Pointer(&u[0])), uintptr(len(u)-1), uintptr(unsafe.Pointer(&r)), uintptr(flags))
	}
	pSelectObject.Call(uintptr(hdc), old)
	pDeleteObject.Call(font)
}
func drawDot(hdc syscall.Handle, x, y int32, hex uint32) {
	b, _, _ := pCreateSolidBrush.Call(color(hex))
	oldb, _, _ := pSelectObject.Call(uintptr(hdc), b)
	pen, _, _ := pGetStockObject.Call(NULL_PEN)
	oldp, _, _ := pSelectObject.Call(uintptr(hdc), pen)
	pEllipse.Call(uintptr(hdc), uintptr(x-5), uintptr(y-5), uintptr(x+5), uintptr(y+5))
	pSelectObject.Call(uintptr(hdc), oldp)
	pSelectObject.Call(uintptr(hdc), oldb)
	pDeleteObject.Call(b)
}
func button(w *nativeWindow, hdc syscall.Handle, id hitID, r RECT, label string, primary bool) {
	bg := uint32(0x171d26)
	border := uint32(0x2b3440)
	fg := uint32(0xeaf2fb)
	if primary {
		bg = 0x1c78ff
		border = 0x3288ff
		fg = 0xffffff
	}
	if w.hover == id {
		if primary {
			bg = 0x2b85ff
		} else {
			bg = 0x202833
		}
	}
	outlineRound(hdc, r, 10, border, bg)
	drawText(hdc, label, r, 15, 600, fg, DT_CENTER|DT_VCENTER|DT_SINGLELINE|DT_END_ELLIPSIS)
	w.hits = append(w.hits, hitRegion{id, r})
}
func toggle(w *nativeWindow, hdc syscall.Handle, id hitID, r RECT, on bool) {
	bg := uint32(0x313b48)
	if on {
		bg = 0x1c78ff
	}
	fillRound(hdc, r, 12, bg)
	x := r.Left + 11
	if on {
		x = r.Right - 11
	}
	dot := RECT{x - 8, r.Top + 4, x + 8, r.Bottom - 4}
	fillRound(hdc, dot, 8, 0xffffff)
	w.hits = append(w.hits, hitRegion{id, r})
}
func statusCard(hdc syscall.Handle, r RECT, title, value string, good bool) {
	outlineRound(hdc, r, 12, 0x252e3a, 0x10161e)
	drawText(hdc, title, RECT{r.Left + 16, r.Top + 12, r.Right - 12, r.Top + 32}, 11, 600, 0x7f8b9a, DT_LEFT|DT_VCENTER|DT_SINGLELINE)
	drawText(hdc, value, RECT{r.Left + 16, r.Top + 36, r.Right - 12, r.Bottom - 12}, 14, 600, 0xe8edf5, DT_LEFT|DT_VCENTER|DT_SINGLELINE|DT_END_ELLIPSIS)
	if good {
		drawDot(hdc, r.Right-18, r.Top+20, 0x42d392)
	}
}

func (w *nativeWindow) paint() {
	var ps PAINTSTRUCT
	hdc, _, _ := pBeginPaint.Call(uintptr(w.hwnd), uintptr(unsafe.Pointer(&ps)))
	defer pEndPaint.Call(uintptr(w.hwnd), uintptr(unsafe.Pointer(&ps)))
	var cr RECT
	pGetClientRect.Call(uintptr(w.hwnd), uintptr(unsafe.Pointer(&cr)))
	dpi, _, _ := pGetDpiForWindow.Call(uintptr(w.hwnd))
	if dpi == 0 {
		dpi = 96
	}
	s := float64(dpi) / 96.0
	// paint in physical coordinates but layout authored at 96 dpi
	b, _, _ := pCreateSolidBrush.Call(color(0x0b1017))
	pFillRect := user32.NewProc("FillRect")
	pFillRect.Call(hdc, uintptr(unsafe.Pointer(&cr)), b)
	pDeleteObject.Call(b)
	w.hits = nil
	lr := func(l, t, r, b int32) RECT { return scaleRect(RECT{l, t, r, b}, s) }
	width := int32(float64(cr.Right-cr.Left) / s)
	locale := w.controller.Settings.Locale
	m := w.controller.Model.Snapshot()
	title, sub := StatusText(&m, locale)
	// header / brand
	drawText(syscall.Handle(hdc), "◇", lr(24, 18, 52, 52), 28, 700, 0x5ca4ff, DT_CENTER|DT_VCENTER|DT_SINGLELINE)
	drawText(syscall.Handle(hdc), "FH6 SCENIC NAVIGATOR", lr(62, 15, width-170, 38), 18, 700, 0xf3f7fb, DT_LEFT|DT_VCENTER|DT_SINGLELINE|DT_END_ELLIPSIS)
	drawText(syscall.Handle(hdc), "Horizon Command", lr(62, 39, width-170, 58), 11, 500, 0x758194, DT_LEFT|DT_VCENTER|DT_SINGLELINE)
	drawText(syscall.Handle(hdc), "v"+AppVersion, lr(width-150, 18, width-78, 48), 11, 600, 0x8d99aa, DT_CENTER|DT_VCENTER|DT_SINGLELINE)
	gear := lr(width-62, 15, width-22, 55)
	button(w, syscall.Handle(hdc), hitSettings, gear, "⚙", false)
	// hero
	hero := lr(24, 78, width-24, 244)
	outlineRound(syscall.Handle(hdc), hero, 16, 0x27313e, 0x0f151d)
	stateColor := uint32(0x6d7785)
	if m.State == Ready {
		stateColor = 0x5ca4ff
	}
	if m.State == Starting {
		stateColor = 0xffba55
	}
	if m.State == Running {
		stateColor = 0x42d392
	}
	if m.State == Error {
		stateColor = 0xff6b77
	}
	drawDot(syscall.Handle(hdc), hero.Left+28, hero.Top+34, stateColor)
	drawText(syscall.Handle(hdc), title, RECT{hero.Left + 48, hero.Top + 17, hero.Right - 24, hero.Top + 52}, 21, 700, 0xf4f7fb, DT_LEFT|DT_VCENTER|DT_SINGLELINE|DT_END_ELLIPSIS)
	drawText(syscall.Handle(hdc), sub, RECT{hero.Left + 48, hero.Top + 50, hero.Right - 24, hero.Top + 82}, 13, 500, 0x9aa6b5, DT_LEFT|DT_VCENTER|DT_SINGLELINE|DT_END_ELLIPSIS)
	if m.State == Ready || m.State == Error {
		button(w, syscall.Handle(hdc), hitStart, RECT{hero.Left + 48, hero.Top + 100, hero.Left + 330, hero.Top + 145}, func() string {
			if m.State == Error {
				return T(locale, "retry")
			}
			return T(locale, "start")
		}(), true)
	}
	if m.State == Running {
		button(w, syscall.Handle(hdc), hitDrive, RECT{hero.Left + 48, hero.Top + 98, hero.Left + 250, hero.Top + 143}, T(locale, "open_drive"), true)
		button(w, syscall.Handle(hdc), hitPlan, RECT{hero.Left + 264, hero.Top + 98, hero.Left + 466, hero.Top + 143}, T(locale, "open_plan"), false)
		button(w, syscall.Handle(hdc), hitStop, RECT{hero.Right - 160, hero.Top + 100, hero.Right - 24, hero.Top + 143}, T(locale, "stop"), false)
	}
	if m.State == Starting {
		stages := []StartupStage{StageRuntime, StageGraph, StageLocalization, StageServer}
		labels := []string{T(locale, "stage_runtime_short"), T(locale, "stage_graph_short"), T(locale, "stage_localization_short"), T(locale, "stage_server_short")}
		x := hero.Left + 48
		for i, st := range stages {
			c := uint32(0x44505f)
			if m.Stage > st {
				c = 0x42d392
			} else if m.Stage == st {
				c = 0xffba55
			}
			drawDot(syscall.Handle(hdc), x+8, hero.Top+117, c)
			drawText(syscall.Handle(hdc), labels[i], RECT{x + 20, hero.Top + 104, x + 116, hero.Top + 132}, 10, 600, 0x8491a2, DT_LEFT|DT_VCENTER|DT_SINGLELINE)
			x += 145
		}
	}
	// 2x2 summary cards
	gap := int32(12)
	left := int32(24)
	right := width - 24
	cw := (right - left - gap) / 2
	locVal := m.Localization
	if locVal == "" {
		locVal = T(locale, "waiting_game")
	}
	places := fmt.Sprintf("%d %s", m.Places, T(locale, "places"))
	if m.Places == 0 {
		places = "823 " + T(locale, "places")
	}
	fh6Value := T(locale, "game_auto")
	if m.State == Running && !m.FH6Found {
		fh6Value = T(locale, "fallback_names")
	}
	statusCard(syscall.Handle(hdc), lr(left, 258, left+cw, 324), T(locale, "fh6"), fh6Value, m.FH6Found)
	statusCard(syscall.Handle(hdc), lr(left+cw+gap, 258, right, 324), T(locale, "localization"), T(locale, "official_names")+" · "+locVal, m.Localization != "")
	statusCard(syscall.Handle(hdc), lr(left, 336, left+cw, 402), T(locale, "navigation"), T(locale, "graph")+" · "+places, m.State == Running)
	net := m.LocalURL
	if net == "" {
		net = fmt.Sprintf("127.0.0.1:%d", w.controller.Settings.HTTPPort)
	}
	if m.LANURL != "" {
		net += "  ·  " + m.LANURL
	}
	statusCard(syscall.Handle(hdc), lr(left+cw+gap, 336, right, 402), T(locale, "network"), net, m.State == Running)
	// log row / panel
	logTop := int32(416)
	logRow := lr(24, logTop, width-24, 458)
	outlineRound(syscall.Handle(hdc), logRow, 10, 0x252e3a, 0x0f151d)
	arrow := "▸"
	if w.logOpen {
		arrow = "▾"
	}
	drawText(syscall.Handle(hdc), arrow+"  "+T(locale, "log"), RECT{logRow.Left + 14, logRow.Top, logRow.Right - 150, logRow.Bottom}, 13, 600, 0xdde4ed, DT_LEFT|DT_VCENTER|DT_SINGLELINE)
	errCount := countErrors(w.controller.Logs())
	logSummary := T(locale, "no_errors")
	if errCount > 0 {
		logSummary = fmt.Sprintf("%d %s", errCount, T(locale, "errors"))
	}
	drawText(syscall.Handle(hdc), logSummary, RECT{logRow.Right - 140, logRow.Top, logRow.Right - 16, logRow.Bottom}, 11, 500, 0x758194, DT_RIGHT|DT_VCENTER|DT_SINGLELINE)
	w.hits = append(w.hits, hitRegion{hitLog, logRow})
	if w.logOpen {
		panel := lr(24, 468, width-24, 590)
		outlineRound(syscall.Handle(hdc), panel, 10, 0x252e3a, 0x0d131a)
		logs := w.controller.Logs()
		start := 0
		if len(logs) > 6 {
			start = len(logs) - 6
		}
		y := panel.Top + 10
		for _, line := range logs[start:] {
			drawText(syscall.Handle(hdc), line, RECT{panel.Left + 14, y, panel.Right - 14, y + 18}, 10, 400, 0x9ba8b8, DT_LEFT|DT_VCENTER|DT_SINGLELINE|DT_END_ELLIPSIS)
			y += 17
		}
		button(w, syscall.Handle(hdc), hitCopyLog, RECT{panel.Right - 250, panel.Bottom - 34, panel.Right - 130, panel.Bottom - 8}, T(locale, "copy_log"), false)
		button(w, syscall.Handle(hdc), hitOpenLogs, RECT{panel.Right - 122, panel.Bottom - 34, panel.Right - 8, panel.Bottom - 8}, T(locale, "open_logs"), false)
	}
	if w.settingsOpen {
		w.paintSettings(syscall.Handle(hdc), lr(width-340, 70, width-18, 590), locale)
	}
}
func countErrors(lines []string) int {
	n := 0
	for _, s := range lines {
		if strings.Contains(strings.ToUpper(s), "ERROR") {
			n++
		}
	}
	return n
}
func (w *nativeWindow) paintSettings(hdc syscall.Handle, r RECT, locale string) {
	outlineRound(hdc, r, 16, 0x354150, 0x111821)
	drawText(hdc, T(locale, "settings"), RECT{r.Left + 20, r.Top + 16, r.Right - 20, r.Top + 48}, 18, 700, 0xf4f7fb, DT_LEFT|DT_VCENTER|DT_SINGLELINE)
	rows := []struct {
		id  hitID
		key string
		on  bool
	}{{hitAutoDrive, "auto_drive", w.controller.Settings.AutoOpenDrive}, {hitMinimize, "minimize", w.controller.Settings.MinimizeAfterOpen}}
	y := r.Top + 64
	for _, row := range rows {
		drawText(hdc, T(locale, row.key), RECT{r.Left + 20, y, r.Right - 72, y + 42}, 12, 500, 0xdbe3ed, DT_LEFT|DT_VCENTER|DT_WORDBREAK)
		toggle(w, hdc, row.id, RECT{r.Right - 62, y + 8, r.Right - 20, y + 32}, row.on)
		y += 52
	}
	drawText(hdc, T(locale, "language"), RECT{r.Left + 20, y, r.Right - 90, y + 38}, 12, 500, 0xdbe3ed, DT_LEFT|DT_VCENTER|DT_SINGLELINE)
	button(w, hdc, hitLocale, RECT{r.Right - 86, y + 4, r.Right - 20, y + 36}, LocaleShort(locale), false)
	y += 56
	drawText(hdc, T(locale, "advanced"), RECT{r.Left + 20, y, r.Right - 20, y + 24}, 10, 700, 0x6f7b8b, DT_LEFT|DT_VCENTER|DT_SINGLELINE)
	drawText(hdc, fmt.Sprintf("HTTP %d  ·  UDP %d", w.controller.Settings.HTTPPort, w.controller.Settings.UDPPort), RECT{r.Left + 20, y + 26, r.Right - 20, y + 52}, 11, 500, 0x9aa6b5, DT_LEFT|DT_VCENTER|DT_SINGLELINE)
	button(w, hdc, hitDone, RECT{r.Left + 20, r.Bottom - 48, r.Right - 20, r.Bottom - 12}, T(locale, "close_settings"), true)
}
