//go:build windows

package launcher_native

import (
	"syscall"
	"unsafe"
)

var trayShell32 = syscall.NewLazyDLL("shell32.dll")
var pNotifyIcon = trayShell32.NewProc("Shell_NotifyIconW")

const trayMessage = WM_APP + 2

func (w *nativeWindow) addTray() {
	if w.trayAdded {
		return
	}
	icon := launcherIcon()
	var n NOTIFYICONDATA
	n.CbSize = uint32(unsafe.Sizeof(n))
	n.HWnd = w.hwnd
	n.UID = 1
	n.UFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
	n.UCallbackMessage = trayMessage
	n.HIcon = icon
	copy(n.SzTip[:], syscall.StringToUTF16("FH6 Scenic Navigator · running"))
	pNotifyIcon.Call(NIM_ADD, uintptr(unsafe.Pointer(&n)))
	w.trayAdded = true
}
func (w *nativeWindow) removeTray() {
	if !w.trayAdded {
		return
	}
	var n NOTIFYICONDATA
	n.CbSize = uint32(unsafe.Sizeof(n))
	n.HWnd = w.hwnd
	n.UID = 1
	pNotifyIcon.Call(NIM_DELETE, uintptr(unsafe.Pointer(&n)))
	w.trayAdded = false
}
func (w *nativeWindow) trayMenu() {
	menu, _, _ := pCreatePopupMenu.Call()
	defer pDestroyMenu.Call(menu)
	items := []struct {
		id   uintptr
		text string
	}{{2001, T(w.controller.Settings.Locale, "open_drive")}, {2002, T(w.controller.Settings.Locale, "open_plan")}, {0, ""}, {2003, T(w.controller.Settings.Locale, "show_launcher")}, {2004, T(w.controller.Settings.Locale, "stop")}, {0, ""}, {2005, T(w.controller.Settings.Locale, "exit")}}
	for _, it := range items {
		if it.id == 0 {
			pAppendMenu.Call(menu, MF_SEPARATOR, 0, 0)
		} else {
			pAppendMenu.Call(menu, MF_STRING, it.id, uintptr(unsafe.Pointer(u16(it.text))))
		}
	}
	var pt POINT
	pGetCursorPos.Call(uintptr(unsafe.Pointer(&pt)))
	pSetForeground.Call(uintptr(w.hwnd))
	pTrackPopupMenu.Call(menu, TPM_RIGHTBUTTON, uintptr(pt.X), uintptr(pt.Y), 0, uintptr(w.hwnd), 0)
}
