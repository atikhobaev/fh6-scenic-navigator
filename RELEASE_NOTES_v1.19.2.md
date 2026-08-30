# FH6 Scenic Navigator v1.19.2 — Process Lifecycle Fix

This release fixes the remaining process-lifecycle issue in the native one-file launcher.

## What's fixed

- Navigator's Python process is attached to a Windows Job Object with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`.
- Closing the launcher now stops Navigator instead of leaving an orphan server on port 8080.
- Stop is asynchronous so the Win32 UI stays responsive while the child process exits.
- Startup can recover a stale previous Navigator process occupying the configured HTTP port.
- Recovery is conservative: a process is terminated automatically only after it is identified as this application's managed Navigator instance. Unrelated software is not killed.
- Lifetime-guard ownership was hardened to avoid Stop/Wait races.

## Portable build

The release executable is a single Windows x64 GUI file containing:

- the FH6 Scenic Navigator application payload;
- the official CPython 3.13.5 x64 embeddable runtime;
- the native Go/Win32 launcher.

No separate Python installation is required for end users.

## Verification

- Python regression suite: 101 tests
- JavaScript regression suite: 149 tests
- Go launcher suite: passing
- Go race detector: passing during release validation
- Embedded Navigator API version: 1.19.2
- Runtime catalog: 823 places (796 game POIs + 27 curated)
- Raw game-owned `.nav/.owt/.oww/.owbs` assets are not included

## SHA-256

`b572350fc09db34e6a601600ceb064e82ad2f9c70c87277b5e7d8bd1f34f8258`
