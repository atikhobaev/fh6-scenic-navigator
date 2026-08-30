# FH6 Scenic Navigator v1.19.0 — Portable Launcher Design

**Date:** 2026-08-30
**Status:** Approved in chat
**Base:** v1.18.2

## Goal
Replace BAT/console startup with one Windows portable launcher EXE that owns startup, status, logs, browser opening, single-instance behavior, and clean shutdown while leaving DRIVE/PLAN in the browser.

## Product UX
The launcher is a quiet control center, not an admin dashboard. Before start it shows one primary action: **Start Navigator**. During startup it shows four human-readable stages. After success it replaces Start with **Open DRIVE**, **Open PLAN**, and a visually secondary **Stop** action.

The main surface always answers four questions: can Navigator start, what is happening, where can I open it, and what failed if something is wrong. Technical details are progressive disclosure under **Launch log**.

## Main window
Target client size ~720x520 logical pixels, DPI-aware and resizable within sensible minimums. Native Windows chrome is retained.

Header:
- product mark and `FH6 Scenic Navigator`;
- `Horizon Command` secondary label;
- `v1.19.0`;
- compact settings button.

Center status area:
- state dot: ready / starting / running / warning / error;
- one-line state title;
- one-line explanatory subtitle;
- primary workflow controls.

Status summary:
- FH6 detection;
- official POI localization coverage for active locale;
- bundled catalog count;
- directed graph readiness;
- local URL;
- LAN URL;
- Forza UDP state (waiting / connected / lost).

Expandable log:
- collapsed by default;
- expands automatically on failure;
- bounded in-memory lines plus persisted UTF-8 log file;
- Copy log and Open logs folder only when expanded.

## Settings
Only four normal settings:
1. Open DRIVE automatically after successful start — default on.
2. Minimize launcher after opening Navigator — default off.
3. Keep Navigator running in tray when window closes — default on.
4. Interface locale — shared with DRIVE/PLAN.

Advanced disclosure:
- HTTP port (default 8080);
- UDP port (default 1234);
- Rescan FH6 installation.

## Tray and lifecycle
Only one launcher instance is allowed. Starting the EXE a second time activates the existing window.

When Navigator is running, tray menu exposes:
- Open DRIVE;
- Open PLAN;
- Show Launcher;
- Stop Navigator;
- Exit.

Closing the window while server is running follows the remembered keep-in-tray preference. Explicit Exit stops the child server and removes tray state.

## Runtime architecture
The portable EXE is a native Win32 launcher compiled with Go. It embeds the Navigator application payload. On first run it extracts immutable application files into `%LOCALAPPDATA%\\FH6 Scenic Navigator\\runtime\\1.19.0` and keeps user-writable database/cache/log files under `%LOCALAPPDATA%\\FH6 Scenic Navigator`.

The launcher starts the Python server hidden and streams stdout/stderr into the GUI log. It polls `/api/info` and `/api/telemetry` for server and game status, and opens ordinary browser URLs for DRIVE/PLAN.

### Python runtime strategy
Preferred self-contained distribution embeds the official CPython Windows embeddable package. The build pipeline accepts `python-3.13.5-embeddable-amd64.zip` and verifies SHA-256 `1786304c00011679a533d3644176b3694f2035b4cc37b0dc09dd226ad9ff5f26` before embedding.

Because the current build host cannot retrieve Windows binary payloads, the launcher also has a secure first-run fallback: if no embedded runtime is present, it downloads that exact official package over HTTPS from python.org, verifies the same SHA-256, and caches it locally. A system Python 3.11+ may be used immediately when already installed. This keeps the distributed launcher as one EXE while preserving a path to a fully offline one-file build when the runtime ZIP is supplied to the build script.

## UI technology
No Qt, Electron, WebView, or external GUI runtime. The launcher uses Win32 APIs from Go with custom-drawn Fluent-inspired surfaces, Segoe UI Variable/Segoe UI fallback, high-DPI layout, keyboard focus, accessible native window behavior, and no frameless chrome.

## Error UX
Errors are translated into actionable product messages first, with raw details in the log. Examples:
- HTTP port occupied by Navigator: offer Open running Navigator;
- HTTP port occupied by another app: explain port conflict;
- Python runtime unavailable: explain preparation/download failure;
- server process exits during startup: show failed stage and auto-expand log;
- StringTables unavailable: warning only, English POI fallback remains usable.

## Non-goals
- embedding DRIVE/PLAN inside the desktop window;
- exposing internal refresh/rebuild buttons in normal UI;
- replacing the browser map renderer;
- implementing an updater service;
- account/cloud features.

## Acceptance criteria
1. User can launch Navigator without BAT or visible console.
2. One EXE owns start/stop/open DRIVE/open PLAN.
3. Startup visibly advances through preparation, localization, routing/server, ready states.
4. Server output is visible in expandable launcher log and persisted on disk.
5. Second launcher invocation focuses the existing instance.
6. Closing-to-tray and explicit exit behave predictably.
7. `/api/info` and `/api/telemetry` drive live status.
8. Browser only opens after HTTP is actually ready.
9. Existing Python and JavaScript suites remain green.
10. Windows EXE cross-compiles on the build host and contains no console subsystem.
