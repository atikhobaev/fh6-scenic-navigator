# Changelog

This history was reconstructed from the project's working chats, saved design/specification files, release artifacts, and the local Git history. Entries describe confirmed user-visible or architectural changes; experimental ideas that were only discussed and not shipped are omitted.

## [1.20.0] - Unreleased — Public Preview

- Added real application captures, a social preview and a user-focused Russian introduction.
- Clarified POI accuracy, map caching and code/data licensing boundaries.
- Closed SQLite connections deterministically on Windows, including the migration test fixture.
- Enabled full pytest collection and Windows Python CI.
- Isolated the Linux FIFO regression test so the Go suite compiles on Windows.
- Copied native Win32 message structures through RtlMoveMemory to avoid integer-to-Go-pointer conversions flagged by go vet.

## [1.19.2] - 2026-08-30 — Process Lifecycle Fix

- Attached the Navigator Python process to a Windows Job Object with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`.
- Closing the launcher now means **Stop Navigator + Exit**; the server is no longer intentionally left running in the background.
- Made Stop asynchronous so waiting for child-process shutdown cannot freeze the Win32 message loop.
- Added stale-process recovery for previous Navigator instances occupying the configured HTTP port.
- Recovery only terminates a process after proving it is FH6 Scenic Navigator (API identity or managed runtime path); unrelated applications are left untouched.
- Hardened lifetime-guard ownership to avoid races between Stop and Wait paths.
- Kept the portable one-file build with embedded CPython and embedded Navigator payload.

## [1.19.1] - 2026-08-30 — Anti-Freeze Fix

- Fixed nondeterministic native launcher hangs by locking the Win32 UI/message-loop goroutine to one OS thread before the first Win32 call.
- Removed disk I/O from the log mutex critical section so repainting the window never waits on logfile writes or antivirus/disk stalls.
- Added anti-freeze regression coverage and race-detector checks.

## [1.19.0] - 2026-08-30 — Native Portable Launcher

- Replaced the BAT-first end-user workflow with a native Windows launcher written in Go/Win32.
- Added a friendly launcher UI with one primary Start action, startup stages, status cards, collapsible logs, DRIVE/PLAN actions, settings, tray support, and single-instance behavior.
- Embedded the complete Navigator application payload into the launcher.
- Embedded the official CPython 3.13.5 x64 embeddable runtime, producing a single portable Windows EXE with no separate Python installation required.
- Added health checks, telemetry status, localization coverage, local/LAN addresses, and human-readable startup errors.
- Fixed custom HTTP-port propagation so preflight and server startup use the same configured port.

## [1.18.2] - 2026-08-30 — Localization Polish & SVG Flags

- Removed generic low-value tooltips; a tooltip is shown only when there is an explicit useful explanation.
- Replaced Unicode flag emoji with bundled SVG flags for reliable rendering on Windows.
- Improved automatic FH6 StringTables discovery for additional Steam libraries and Xbox App installations.
- Added localization coverage diagnostics for the 796 game POIs.
- Kept strict localization fallback: selected official game localization -> official English -> safe canonical fallback; no machine-translated or guessed POI names.

## [1.18.1] - 2026-08-30 — UI Polish & Tooltips

- Fixed DRIVE destination labels so internal IDs such as `builtin.game...` are not exposed as user-facing names.
- Made toolbar controls adaptive instead of relying on rigid text-button widths.
- Moved language selection into the compact status area and synchronized it across DRIVE and PLAN.
- Added a shared tooltip system for meaningful button explanations, including dynamic route-editor actions.

## [1.18.0] - 2026-08-30 — Horizon Command UI & Internationalization

- Refactored DRIVE and PLAN around a shared Tailwind v4 design system and a more polished Horizon Command visual language.
- Added English, Simplified Chinese, Russian, and Latin American Spanish UI localization.
- Added a shared locale store and live language switching without page reloads.
- Added an FH6 StringTable importer for official game-name localization with English fallback.
- Rebuilt Planner search indexes when locale changes so localized POI names are actually searchable.
- Preserved Directed WVAN as the routing authority while changing only the presentation/i18n layers.

## [1.17.2] - 2026-08-30 — Full POI Inventory & UI Fixes

- Bundled a full working inventory of **796 game POIs** plus 27 curated scenic destinations.
- Kept 24 Barn Find/Treasure Car locations on their published exact coordinates; the pet-project inventory expanded the remaining categories to make the complete layer/filter system usable.
- Fixed map context-menu dismissal and marker click/drag interaction.
- Added progress output for longer local operations so the launcher does not appear stalled.

## [1.17.1] - 2026-08-30 — Offline Data & Progress

- Removed mandatory runtime/bootstrap downloads for POI, screenshots, and road data.
- Bundled the runtime road dataset, POI catalogs, and compiled Directed WVAN graph.
- Converted `update_map_data.bat` into a local rebuild workflow rather than an internet downloader.
- Added explicit progress stages and atomic catalog publication.
- Kept only verified/provable coordinate records in the normal runtime pipeline; uncertain coordinates were not guessed.

## [1.17.0] - 2026-08-30 — Complete Map, Offline Media & Gesture Arbitration

- Defined/implemented marker gesture arbitration: click selects a marker; dragging >=5 CSS px pans the map even when starting on a marker.
- Expanded the build-time multi-source POI ingestion model while keeping runtime data normalized and local.
- Added an offline media pipeline for cached place images and text-only fallbacks when images are unavailable.
- Preserved source provenance, exact-position requirements, WVAN snapping, and fail-closed behavior for unproven coordinates.
- Added performance targets for dense ~1,000+ POI maps and kept route/selected markers out of clustering.

## [1.16.3] - 2026-08-29 — SVG Icons, Low-Zoom Map & Quiet Console

- Replaced Windows font-symbol POI markers with bundled SVG category icons.
- Reused the same icon system in markers, layer controls, and search results.
- Improved low-zoom map behavior by deriving lower zoom levels from available tiles rather than requesting invalid upstream zooms.
- Reduced normal browser/network cancellation noise in the console.

## [1.16.2] - 2026-08-29 — Startup & UI Fixes

- Added a consistent `DRIVE | PLAN` mode switch to both screens and removed the duplicated PLAN button.
- Fixed multi-group filter collapsing and added Collapse all / Expand all.
- Changed startup so the browser opens only after the local HTTP/UDP services are ready.
- Added no-store headers/version display to reduce stale browser assets during rapid development.

## [1.16.0] - 2026-08-29 — Map-First Planner

- Redesigned PLAN around the map as the primary surface.
- Added grouped POI layers, Recommended / Enable all / Disable all presets, persistent filter state, and full-catalog search.
- Added on-map POI popovers with route/favorite/destination actions instead of a separate details page.
- Kept selected and active-route markers visible regardless of layer filters/clustering.
- Added the built-in **Grand Tour Japan** 27-stop route to Planner, with direct start and copy-on-first-edit behavior.
- Added/updated SQLite route/session persistence and an offline community evidence/import pipeline.
- Kept Directed WVAN as the only active authoritative router.

## [1.15.0] - 2026-08-29 — Route Planner & Places Library

- Introduced the dedicated PLAN workspace alongside DRIVE.
- Added the Places Library foundation with search/filtering, favorites, curated content, My Places, and route construction.
- Added route item editing/reordering, reverse/optimization/undo-redo concepts, saved routes/drafts, SQLite persistence, and live route preview using Directed WVAN.
- Established the rule that Planner edits must never bypass legal directed routing and that unresolved routes cannot be started.

## [1.14.0] - 2026-08-28 — Directed WVAN Routing

- Replaced the active bidirectional LabsGG router with a compiled `fh6-navgraph-v1` derived from locally owned FH6 `Brio_00.nav` data.
- Compiled **38,473 NavPoints** and **71,222 directed road segments** for the validated graph used by the Navigator.
- Honored `oneway_forward`, junction identity, and proven turn restrictions such as `no_right_turn`.
- Added directed map matching using car X/Z position, yaw, and previous-segment continuity.
- Added automatic legal rerouting after leaving guidance.
- Added fail-closed behavior: if a legal directed path cannot be found, active navigation does not silently fall back to the old bidirectional graph.
- Raw game navigation assets were explicitly excluded from distribution; only compiled graph data/fingerprints are shipped.

## [1.13.0] - 2026-08-28 — NAV Binary Probe

- Added a read-only binary probe for `Brio_00.nav` and representative `Route*.nav` samples.
- Added diagnostics/report generation to support reverse engineering of WVAN structure without modifying game files.

## [1.12.0] - 2026-08-28 — Game Navigation Asset Probe

- Added a read-only diagnostic tool for locating and inventorying FH6 navigation assets.
- Prepared the evidence-gathering workflow that led to Directed WVAN routing.

## [1.10.x] - 2026-08-28 — Directed Routing Research

- Investigated ForzaLabs `routeNodes` as a possible source for direction/transition semantics.
- Established a fail-closed capability gate: direction must be proven from data rather than inferred from parallel-road geometry.
- This research led to the later decision to derive authoritative directionality from FH6 WVAN navigation data instead.

## [1.9.0] - 2026-08-28 — Scenic Route Ordering

- Changed POI ordering so the route is refined according to which POI road nodes the computed loop naturally reaches first.
- Expanded the default Grand Tour into the eastern/right side of the map.
- Added strong asphalt preference, penalties for reusing roads, and avoidance of immediate edge reversal when alternatives exist.
- Added remaining-leg guidance, selectable next POI, clockwise/counter-clockwise tour direction, turn-warning intensity at 500/300/100 m, and speed-sensitive autozoom.

## [1.3.x] - 2026-08-28 — Road-Based Scenic Loop Foundation

- Replaced straight waypoint-to-waypoint guidance with routing along a road graph.
- Snapped scenic waypoints to road nodes and used weighted Dijkstra routing.
- Preferred asphalt while allowing dirt/snow when needed.
- Added loop closure and guidance along the computed route polyline.
- This version still used the earlier bidirectional external road representation; authoritative Directed WVAN arrived later in v1.14.
