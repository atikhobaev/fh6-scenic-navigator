# FH6 Scenic Navigator v1.19.0 Portable Launcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a friendly native Windows one-file launcher that starts, monitors, and stops FH6 Scenic Navigator without BAT/console workflow.

**Architecture:** A Go `launcher_native` package owns the state machine, payload extraction, runtime resolution, child server process, health polling and user settings. A Windows-only Win32 front-end renders the approved Horizon Command launcher and tray. Navigator browser/server code remains authoritative and is bundled as immutable payload.

**Tech Stack:** Go 1.23 stdlib + Win32 syscall APIs, embedded zip payload, existing Python 3.13-compatible server, Node tests, Python unittest.

**Spec:** `docs/superpowers/specs/2026-08-30-v119-portable-launcher-design.md`

## Global Constraints
- Preserve all v1.18.2 DRIVE/PLAN and Directed-WVAN behavior.
- No Qt, Electron, WebView, or browser embedding in launcher.
- No visible console during normal Windows use.
- One launcher instance only.
- Runtime user data lives under `%LOCALAPPDATA%\\FH6 Scenic Navigator`.
- Browser opens only after server health succeeds.
- Release EXE must contain the exact verified CPython 3.13.5 x64 embedded runtime; system Python/download fallback is development/bootstrap-only and must never satisfy the release gate.

---

### Task 1: Launcher state model and settings
**Files:** create `launcher_native/state.go`, `launcher_native/settings.go`, `launcher_native/state_test.go`.
**Produces:** typed launcher states, progress steps, settings defaults/load/save, derived button visibility.
- [ ] Write failing Go tests for Ready/Starting/Running/Error transitions and four settings defaults.
- [ ] Run `go test ./launcher_native` and confirm RED.
- [ ] Implement minimal state/settings model.
- [ ] Re-run and confirm GREEN.
- [ ] Commit.

### Task 2: Payload extraction and runtime resolver
**Files:** create `launcher_native/payload.go`, `launcher_native/runtime.go`, tests; create `launcher_payload/manifest.json`; add `scripts/build_launcher_payload.py`.
**Produces:** deterministic runtime directory, versioned payload extraction, system Python discovery, verified CPython-download metadata.
- [ ] Write failing tests for versioned extraction marker, Python candidate order, and SHA-256 verifier.
- [ ] Verify RED.
- [ ] Implement extraction/resolver and payload builder.
- [ ] Verify GREEN and generated payload manifest.
- [ ] Commit.

### Task 3: Server lifecycle and health polling
**Files:** create `launcher_native/server.go`, `launcher_native/health.go`, tests; modify `server.py` version to 1.19.0; add writable-root support through environment.
**Produces:** start/stop child process, streamed logs, `/api/info` + `/api/telemetry` monitoring, browser-ready event.
- [ ] Write failing Go tests using a fake child/HTTP server for ready, early exit, stop and telemetry status.
- [ ] Verify RED.
- [ ] Implement lifecycle/health code and minimal Python writable-root plumbing.
- [ ] Verify GREEN plus existing Python suite.
- [ ] Commit.

### Task 4: Native Win32 Horizon Command window
**Files:** create `launcher_native/main_windows.go`, `win32_windows.go`, `paint_windows.go`, `tray_windows.go`, `ui_model.go`; create `cmd/fh6-launcher/main.go`; non-Windows stub for tests.
**Produces:** DPI-aware native window, custom cards/buttons, progressive log, tray, single-instance activation.
- [ ] Write platform-neutral UI-model tests for pre-start, starting, running and error action sets.
- [ ] Verify RED.
- [ ] Implement UI model, then Windows rendering and hit-testing around the model.
- [ ] Cross-compile `GOOS=windows GOARCH=amd64 go build -ldflags='-H=windowsgui'` and require success.
- [ ] Commit.

### Task 5: Packaging and release scripts
**Files:** create `scripts/build_portable_launcher.sh`, `launcher_native/embed.go`, generated `launcher_payload/app_payload.zip`; update README/HOW_TO_START; remove BAT files from portable release manifest but retain source compatibility.
**Produces:** `FH6 Scenic Navigator.exe`, with app payload embedded and the verified CPython 3.13.5 x64 embedded runtime included inside the EXE.
- [ ] Add failing package validation test that checks PE header, GUI subsystem build command, payload presence and version metadata.
- [ ] Verify RED.
- [ ] Implement deterministic payload generation and Windows build.
- [ ] Verify GREEN and inspect EXE with `file`/hash.
- [ ] Commit.

### Task 6: Full regression and release handoff
**Files:** release artifact only.
**Produces:** merged master and user-visible EXE.
- [ ] Run `python -m unittest discover -s tests -p 'test_*.py'`.
- [ ] Run `npm run test:js`.
- [ ] Run `go test ./...`.
- [ ] Cross-compile final Windows GUI EXE from clean tree.
- [ ] Verify payload archive has no `.git`, test caches, raw game `.nav/.owt/.oww/.owbs`, or runtime secrets.
- [ ] Merge locally to master and repeat all source-level tests.
