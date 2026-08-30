# FH6 Scenic Navigator

**Local companion navigator and route planner for Forza Horizon 6.**

FH6 Scenic Navigator runs alongside the game and provides a clean external map, route planning, telemetry-driven navigation, and turn-by-turn guidance without requiring the in-game HUD. The current Windows release is distributed as a **single portable EXE** that opens the DRIVE / PLAN interface in the user's normal browser.

> Status: personal/private pet project. Not affiliated with Microsoft, Xbox, Playground Games, Turn 10 Studios, or the Forza brand.

## Highlights

- **DRIVE mode** — low-distraction navigation view for a second monitor, tablet, or phone.
- **PLAN mode** — map-first route planner with search, filters, POI popovers, route editing, favorites, and saved routes.
- **Directed WVAN routing** — authoritative routing uses a compiled directed graph derived from locally owned FH6 navigation data; no bidirectional fallback is used for active guidance when Directed WVAN is unavailable.
- **823 runtime places** — 796 game POIs plus 27 curated scenic destinations in the current catalog.
- **Multilingual UI** — English, Simplified Chinese, Russian, and Latin American Spanish.
- **Official game-name localization where provable** — StringTables are read locally when FH6 is installed; unresolved POIs safely fall back to English rather than being machine-translated or guessed.
- **Portable Windows launcher** — one EXE, embedded CPython runtime, live startup status/logs, single-instance behavior, and clean child-process lifecycle management.
- **Offline-first runtime data** — POI catalogs, Directed WVAN graph, UI assets, and cached media are bundled; no runtime POI scraping is required.

## Latest release — v1.19.2

The current portable launcher focuses on process lifecycle reliability:

- Navigator's Python process is attached to a Windows Job Object with `KILL_ON_JOB_CLOSE`.
- Closing the launcher stops Navigator instead of leaving an orphan server on port 8080.
- Stop is asynchronous so the Win32 UI remains responsive.
- Startup can recover a stale previous Navigator process only after proving that it belongs to this application.
- Unrelated applications using the configured HTTP port are never terminated automatically.

Download the executable from **GitHub Releases** after this repository is published.

## Quick start

### Portable release

1. Download `FH6_Scenic_Navigator_v1.19.2_PORTABLE_PROCESS_LIFECYCLE_FIX.exe` from Releases.
2. Run it on Windows 10/11 x64.
3. Click **Start Navigator**.
4. Open **DRIVE** or **PLAN** from the launcher.
5. In Forza Horizon 6 enable Data Out and use the IP/UDP port shown by the launcher.

The portable build contains the official CPython 3.13.5 embeddable runtime and does not require a separate Python installation.

### Run from source

For development, Python 3.10+ is sufficient for the server/runtime code. Go is required only to build the native Windows launcher.

```bash
python launcher.py
```

The browser UI is plain HTML/CSS/JavaScript. Node.js is only used for the JavaScript test suite and Tailwind build tooling; it is not required by end users.

## Architecture

```text
FH6 Data Out (UDP)
        |
        v
   Python server  ---- Directed WVAN graph / POI catalog / SQLite
        |
        +---- /            -> DRIVE
        +---- /planner/    -> PLAN
        +---- /api/*       -> navigation / route / places APIs

Windows portable launcher (Go / Win32)
        |
        +---- embedded CPython runtime
        +---- embedded Navigator payload
        +---- process lifecycle / logs / status / browser launch
```

### Routing authority

The active navigation path is produced from `fh6-navgraph-v1`, a directed graph compiled from locally owned FH6 WVAN navigation data. The repository contains only the compiled application representation and non-copyrightable validation fingerprints; raw game-owned `.nav`, `.owt`, `.oww`, and `.owbs` files are intentionally excluded.

## Repository layout

```text
cmd/fh6-launcher/          native Windows launcher entrypoint
launcher_native/          launcher UI, runtime extraction, lifecycle and tests
fh6_nav/                  WVAN parsing / compiled graph tooling
static/                   DRIVE / PLAN frontend, i18n, POI catalogs and assets
tools/                    build-time import / catalog tools
tests/                    Python and JavaScript regression suites
server.py                 local HTTP + telemetry server
launcher.py               source/development startup wrapper
docs/superpowers/         design specifications and implementation plans
```

## Tests

```bash
python -m unittest discover -s tests -p 'test_*.py'
npm run test:js
go test ./...
```

The release process also validates catalog integrity, Directed WVAN availability, HTTP health, embedded payloads, and the absence of raw FH6 navigation assets.

## Data and third-party sources

The project uses public factual map/location references and locally owned game data for interoperability and navigation research. Runtime catalogs retain provenance where applicable. See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) for details.

No raw FH6 game navigation files are distributed in this repository or releases.

## Version history

See [`CHANGELOG.md`](CHANGELOG.md) for the reconstructed development history from the project chats, design documents, release artifacts, and Git history.

For the longer Russian technical notes, see [`README_RU.md`](README_RU.md).
