//go:build windows

package launcher_native

import (
	"syscall"
)

type POINT struct{ X, Y int32 }
type RECT struct{ Left, Top, Right, Bottom int32 }
type MSG struct {
	Hwnd           syscall.Handle
	Message        uint32
	WParam, LParam uintptr
	Time           uint32
	Pt             POINT
	LPrivate       uint32
}
type WNDCLASSEX struct {
	CbSize                                   uint32
	Style                                    uint32
	LpfnWndProc                              uintptr
	CbClsExtra, CbWndExtra                   int32
	HInstance, HIcon, HCursor, HbrBackground syscall.Handle
	LpszMenuName, LpszClassName              *uint16
	HIconSm                                  syscall.Handle
}
type MINMAXINFO struct {
	PtReserved, PtMaxSize, PtMaxPosition, PtMinTrackSize, PtMaxTrackSize POINT
}
type PAINTSTRUCT struct {
	Hdc                syscall.Handle
	Erase              int32
	RcPaint            RECT
	Restore, IncUpdate int32
	RgbReserved        [32]byte
}
type NOTIFYICONDATA struct {
	CbSize                        uint32
	HWnd                          syscall.Handle
	UID, UFlags, UCallbackMessage uint32
	HIcon                         syscall.Handle
	SzTip                         [128]uint16
	DwState, DwStateMask          uint32
	SzInfo                        [256]uint16
	UVersion                      uint32
	SzInfoTitle                   [64]uint16
	DwInfoFlags                   uint32
	GuidItem                      [16]byte
	HBalloonIcon                  syscall.Handle
}

var user32 = syscall.NewLazyDLL("user32.dll")
var gdi32 = syscall.NewLazyDLL("gdi32.dll")
var kernel32 = syscall.NewLazyDLL("kernel32.dll")
var dwmapi = syscall.NewLazyDLL("dwmapi.dll")
var (
	pRegisterClassEx  = user32.NewProc("RegisterClassExW")
	pCreateWindowEx   = user32.NewProc("CreateWindowExW")
	pDefWindowProc    = user32.NewProc("DefWindowProcW")
	pShowWindow       = user32.NewProc("ShowWindow")
	pUpdateWindow     = user32.NewProc("UpdateWindow")
	pGetMessage       = user32.NewProc("GetMessageW")
	pTranslateMessage = user32.NewProc("TranslateMessage")
	pDispatchMessage  = user32.NewProc("DispatchMessageW")
	pPostQuit         = user32.NewProc("PostQuitMessage")
	pBeginPaint       = user32.NewProc("BeginPaint")
	pEndPaint         = user32.NewProc("EndPaint")
	pInvalidate       = user32.NewProc("InvalidateRect")
	pGetClientRect    = user32.NewProc("GetClientRect")
	pGetWindowRect    = user32.NewProc("GetWindowRect")
	pLoadCursor       = user32.NewProc("LoadCursorW")
	pLoadIcon         = user32.NewProc("LoadIconW")
	pCreateIconRes    = user32.NewProc("CreateIconFromResourceEx")
	pDestroyWindow    = user32.NewProc("DestroyWindow")
	pPostMessage      = user32.NewProc("PostMessageW")
	pSetForeground    = user32.NewProc("SetForegroundWindow")
	pFindWindow       = user32.NewProc("FindWindowW")
	pIsIconic         = user32.NewProc("IsIconic")
	pGetDpiForWindow  = user32.NewProc("GetDpiForWindow")
	pGetDpiForSystem  = user32.NewProc("GetDpiForSystem")
	pSetDpiContext    = user32.NewProc("SetProcessDpiAwarenessContext")
	pSetCursor        = user32.NewProc("SetCursor")
	pTrackPopupMenu   = user32.NewProc("TrackPopupMenu")
	pCreatePopupMenu  = user32.NewProc("CreatePopupMenu")
	pAppendMenu       = user32.NewProc("AppendMenuW")
	pDestroyMenu      = user32.NewProc("DestroyMenu")
	pGetCursorPos     = user32.NewProc("GetCursorPos")
	pSetWindowPos     = user32.NewProc("SetWindowPos")
	pGetModuleHandle  = kernel32.NewProc("GetModuleHandleW")
	pCreateMutex      = kernel32.NewProc("CreateMutexW")
	pGetLastError     = kernel32.NewProc("GetLastError")
	pCreateSolidBrush = gdi32.NewProc("CreateSolidBrush")
	pDeleteObject     = gdi32.NewProc("DeleteObject")
	pSelectObject     = gdi32.NewProc("SelectObject")
	pRoundRect        = gdi32.NewProc("RoundRect")
	pSetBkMode        = gdi32.NewProc("SetBkMode")
	pSetTextColor     = gdi32.NewProc("SetTextColor")
	pDrawText         = user32.NewProc("DrawTextW")
	pCreateFont       = gdi32.NewProc("CreateFontW")
	pEllipse          = gdi32.NewProc("Ellipse")
	pGetStockObject   = gdi32.NewProc("GetStockObject")
)
var pDwmSetWindowAttribute = dwmapi.NewProc("DwmSetWindowAttribute")

const (
	WM_DESTROY          = 0x0002
	WM_PAINT            = 0x000F
	WM_CLOSE            = 0x0010
	WM_GETMINMAXINFO    = 0x0024
	WM_COMMAND          = 0x0111
	WM_LBUTTONUP        = 0x0202
	WM_MOUSEMOVE        = 0x0200
	WM_DPICHANGED       = 0x02E0
	WM_APP              = 0x8000
	WS_OVERLAPPEDWINDOW = 0x00CF0000
	WS_VISIBLE          = 0x10000000
	CW_USEDEFAULT       = 0x80000000
	SW_SHOW             = 5
	SW_RESTORE          = 9
	SW_HIDE             = 0
	SW_MINIMIZE         = 6
	DT_LEFT             = 0x0000
	DT_CENTER           = 0x0001
	DT_RIGHT            = 0x0002
	DT_VCENTER          = 0x0004
	DT_WORDBREAK        = 0x0010
	DT_SINGLELINE       = 0x0020
	DT_END_ELLIPSIS     = 0x8000
	TRANSPARENT         = 1
	NULL_PEN            = 8
	NIM_ADD             = 0
	NIM_DELETE          = 2
	NIF_MESSAGE         = 1
	NIF_ICON            = 2
	NIF_TIP             = 4
	TPM_RIGHTBUTTON     = 2
	MF_STRING           = 0
	MF_SEPARATOR        = 0x800
)

func u16(s string) *uint16     { p, _ := syscall.UTF16PtrFromString(s); return p }
func rgb(r, g, b byte) uintptr { return uintptr(r) | uintptr(g)<<8 | uintptr(b)<<16 }
func loWord(v uintptr) int32   { return int32(int16(v & 0xffff)) }
func hiWord(v uintptr) int32   { return int32(int16((v >> 16) & 0xffff)) }
func rectContains(r RECT, x, y int32) bool {
	return x >= r.Left && x < r.Right && y >= r.Top && y < r.Bottom
}
func post(hwnd syscall.Handle, msg uint32) { pPostMessage.Call(uintptr(hwnd), uintptr(msg), 0, 0) }
func invalidate(hwnd syscall.Handle)       { pInvalidate.Call(uintptr(hwnd), 0, 0) }
