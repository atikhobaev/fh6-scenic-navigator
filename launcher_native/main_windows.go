//go:build windows

package launcher_native

import (
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"syscall"
	"unsafe"
)

const className = "FH6ScenicNavigatorLauncherWindow"

var currentWindow *nativeWindow

func launcherIcon() syscall.Handle {
	if len(EmbeddedIconPNG) > 0 {
		if h, _, _ := pCreateIconRes.Call(uintptr(unsafe.Pointer(&EmbeddedIconPNG[0])), uintptr(len(EmbeddedIconPNG)), 1, 0x00030000, 256, 256, 0); h != 0 {
			return syscall.Handle(h)
		}
	}
	h, _, _ := pLoadIcon.Call(0, 32512)
	return syscall.Handle(h)
}

func RunLauncher() {
	runtime.LockOSThread()
	defer runtime.UnlockOSThread()
	pSetDpiContext.Call(^uintptr(3), 0, 0) // DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 == -4
	if !acquireSingleInstance() {
		return
	}
	hinst, _, _ := pGetModuleHandle.Call(0)
	cls := u16(className)
	title := u16("FH6 Scenic Navigator")
	cursor, _, _ := pLoadCursor.Call(0, 32512)
	icon := launcherIcon()
	wc := WNDCLASSEX{CbSize: uint32(unsafe.Sizeof(WNDCLASSEX{})), Style: 3, LpfnWndProc: syscall.NewCallback(wndProc), HInstance: syscall.Handle(hinst), HIcon: icon, HCursor: syscall.Handle(cursor), LpszClassName: cls, HIconSm: icon}
	if r, _, _ := pRegisterClassEx.Call(uintptr(unsafe.Pointer(&wc))); r == 0 {
		return
	}
	dpi, _, _ := pGetDpiForSystem.Call()
	if dpi == 0 {
		dpi = 96
	}
	logicalW, logicalH := DefaultWindowLogicalSize()
	winW := uintptr(logicalW * int(dpi) / 96)
	winH := uintptr(logicalH * int(dpi) / 96)
	hwnd, _, _ := pCreateWindowEx.Call(0, uintptr(unsafe.Pointer(cls)), uintptr(unsafe.Pointer(title)), WS_OVERLAPPEDWINDOW|WS_VISIBLE, CW_USEDEFAULT, CW_USEDEFAULT, winW, winH, 0, 0, hinst, 0)
	if hwnd == 0 {
		return
	}
	w := &nativeWindow{hwnd: syscall.Handle(hwnd)}
	currentWindow = w
	w.controller = NewController(func() { post(w.hwnd, WM_APP+1) })
	dark := int32(1)
	pDwmSetWindowAttribute.Call(hwnd, 20, uintptr(unsafe.Pointer(&dark)), 4)
	pShowWindow.Call(hwnd, SW_SHOW)
	pUpdateWindow.Call(hwnd)
	var msg MSG
	for {
		r, _, _ := pGetMessage.Call(uintptr(unsafe.Pointer(&msg)), 0, 0, 0)
		if int32(r) <= 0 {
			break
		}
		pTranslateMessage.Call(uintptr(unsafe.Pointer(&msg)))
		pDispatchMessage.Call(uintptr(unsafe.Pointer(&msg)))
	}
}
func acquireSingleInstance() bool {
	name := u16("Local\\FH6ScenicNavigatorLauncher_v119")
	_, _, _ = pCreateMutex.Call(0, 0, uintptr(unsafe.Pointer(name)))
	e, _, _ := pGetLastError.Call()
	if e != 183 {
		return true
	}
	cls := u16(className)
	if h, _, _ := pFindWindow.Call(uintptr(unsafe.Pointer(cls)), 0); h != 0 {
		if r, _, _ := pIsIconic.Call(h); r != 0 {
			pShowWindow.Call(h, SW_RESTORE)
		} else {
			pShowWindow.Call(h, SW_SHOW)
		}
		pSetForeground.Call(h)
	}
	return false
}
func wndProc(hwnd syscall.Handle, msg uint32, wparam, lparam uintptr) uintptr {
	w := currentWindow
	if w == nil && msg != WM_DESTROY {
		r, _, _ := pDefWindowProc.Call(uintptr(hwnd), uintptr(msg), wparam, lparam)
		return r
	}
	switch msg {
	case WM_PAINT:
		w.paint()
		return 0
	case WM_APP + 1:
		snap := w.controller.Model.Snapshot()
		if snap.State == Error && !w.logOpen {
			w.logOpen = true
			resizeForLog(w)
		}
		invalidate(hwnd)
		if snap.State == Running {
			w.addTray()
			if w.controller.Settings.AutoOpenDrive && w.controller.Settings.MinimizeAfterOpen && !w.autoMinimized {
				pShowWindow.Call(uintptr(hwnd), SW_MINIMIZE)
				w.autoMinimized = true
			}
		} else if snap.State == Ready {
			w.autoMinimized = false
		}
		return 0
	case WM_MOUSEMOVE:
		x, y := loWord(lparam), hiWord(lparam)
		id := hitNone
		for _, h := range w.hits {
			if rectContains(h.r, x, y) {
				id = h.id
				break
			}
		}
		if id != w.hover {
			w.hover = id
			invalidate(hwnd)
		}
		return 0
	case WM_LBUTTONUP:
		w.click(loWord(lparam), hiWord(lparam))
		return 0
	case WM_COMMAND:
		w.command(uint32(wparam & 0xffff))
		return 0
	case trayMessage:
		if lparam == 0x0205 || lparam == 0x0202 {
			w.trayMenu()
		} else if lparam == 0x0203 {
			pShowWindow.Call(uintptr(hwnd), SW_SHOW)
			pSetForeground.Call(uintptr(hwnd))
		}
		return 0
	case WM_GETMINMAXINFO:
		info := (*MINMAXINFO)(unsafe.Pointer(lparam))
		dpi, _, _ := pGetDpiForWindow.Call(uintptr(hwnd))
		if dpi == 0 {
			dpi = 96
		}
		mw, mh := MinimumWindowLogicalSize()
		info.PtMinTrackSize = POINT{X: int32(mw * int(dpi) / 96), Y: int32(mh * int(dpi) / 96)}
		return 0
	case WM_DPICHANGED:
		r := (*RECT)(unsafe.Pointer(lparam))
		pSetWindowPos.Call(uintptr(hwnd), 0, uintptr(r.Left), uintptr(r.Top), uintptr(r.Right-r.Left), uintptr(r.Bottom-r.Top), 0x0004)
		return 0
	case WM_CLOSE:
		w.controller.StopAsync()
		w.removeTray()
		pDestroyWindow.Call(uintptr(hwnd))
		return 0
	case WM_DESTROY:
		w.removeTray()
		pPostQuit.Call(0)
		return 0
	}
	r, _, _ := pDefWindowProc.Call(uintptr(hwnd), uintptr(msg), wparam, lparam)
	return r
}
func (w *nativeWindow) click(x, y int32) {
	for _, h := range w.hits {
		if !rectContains(h.r, x, y) {
			continue
		}
		switch h.id {
		case hitStart:
			w.controller.Start()
		case hitDrive:
			w.controller.OpenDrive()
			if w.controller.Settings.MinimizeAfterOpen {
				pShowWindow.Call(uintptr(w.hwnd), SW_MINIMIZE)
			}
		case hitPlan:
			w.controller.OpenPlan()
			if w.controller.Settings.MinimizeAfterOpen {
				pShowWindow.Call(uintptr(w.hwnd), SW_MINIMIZE)
			}
		case hitStop:
			w.controller.StopAsync()
		case hitSettings:
			w.settingsOpen = !w.settingsOpen
		case hitLog:
			w.logOpen = !w.logOpen
			resizeForLog(w)
		case hitCopyLog:
			CopyText(strings.Join(w.controller.Logs(), "\r\n"))
		case hitOpenLogs:
			OpenFolder(filepath.Dir(w.controller.LogPath()))
		case hitAutoDrive:
			w.controller.Settings.AutoOpenDrive = !w.controller.Settings.AutoOpenDrive
			w.controller.SaveSettings()
		case hitMinimize:
			w.controller.Settings.MinimizeAfterOpen = !w.controller.Settings.MinimizeAfterOpen
			w.controller.SaveSettings()
		case hitLocale:
			w.controller.Settings.Locale = NextLocale(w.controller.Settings.Locale)
			w.controller.SaveSettings()
		case hitDone:
			w.settingsOpen = false
		}
		invalidate(w.hwnd)
		return
	}
}
func resizeForLog(w *nativeWindow) {
	dpi, _, _ := pGetDpiForWindow.Call(uintptr(w.hwnd))
	if dpi == 0 {
		dpi = 96
	}
	var r RECT
	pGetWindowRect.Call(uintptr(w.hwnd), uintptr(unsafe.Pointer(&r)))
	width := r.Right - r.Left
	height := int32(WindowLogicalHeight(w.logOpen) * int(dpi) / 96)
	pSetWindowPos.Call(uintptr(w.hwnd), 0, 0, 0, uintptr(width), uintptr(height), 0x0002|0x0004)
}
func (w *nativeWindow) command(id uint32) {
	switch id {
	case 2001:
		w.controller.OpenDrive()
	case 2002:
		w.controller.OpenPlan()
	case 2003:
		pShowWindow.Call(uintptr(w.hwnd), SW_SHOW)
		pSetForeground.Call(uintptr(w.hwnd))
	case 2004:
		w.controller.StopAsync()
	case 2005:
		w.controller.StopAsync()
		w.removeTray()
		pDestroyWindow.Call(uintptr(w.hwnd))
	}
}

var _ = os.PathSeparator
