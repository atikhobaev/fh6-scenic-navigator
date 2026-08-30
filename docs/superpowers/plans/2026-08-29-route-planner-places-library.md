# FH6 Route Planner + Places Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Planner v1 as a local desktop-first `/planner` application with a large pre-populated Places Library, SQLite-backed routes/favorites/My Places, directed WVAN previews, Scenic blocks, revisions/Undo, live PLAN↔DRIVE synchronization, navigation sessions, import/export, and release-safe packaging.

**Architecture:** Preserve the existing DRIVE page and directed WVAN authority. Add modular Python planner services around SQLite/JSON catalogs plus REST/SSE, and a separate modular browser application under `static/planner/`. Internet POI ingestion is a build-time tool that emits validated versioned catalogs; runtime remains offline and fail-closed.

**Tech Stack:** Python 3 stdlib (`sqlite3`, `http.server`, `json`, `gzip`, `threading`), existing `fh6_nav` compiled graph, browser ES modules, HTML/CSS, Node `node:test`.

**Spec:** `docs/superpowers/specs/2026-08-29-route-planner-places-library-design.md`

## Global Constraints

- Existing DRIVE behavior and Directed WVAN safety rules remain regression-protected.
- Raw game-owned `.nav/.owt/.oww/.owbs` files must never ship in the release.
- Runtime internet scraping is forbidden; catalog import runs only as a build/development tool.
- Planner v1 remains local-only and desktop-first; Cloud/Bridge, accounts, translations, Near Me, Search This Area, community features, full mobile Planner, and Scenic optimization profile are out of scope.
- A route preview must never fall back to legacy LabsGG `shortestPath` when WVAN has no legal directed path.
- User data lives in `data/navigator.db`; built-in and curated content are replaceable versioned JSON catalogs.
- Every route mutation is revisioned and atomic; API writes use `expected_revision` and return HTTP 409 on stale writes.
- Scenic Road/Loop blocks are indivisible at the Route Item level and preserve their mandatory directed internal path.
- Search/filter operations must remain responsive for at least 3,000 catalog entries.

---

## Phase 1 — SQLite, Core Models, REST Foundation

### Task 1: SQLite schema and migrations

**Files:**
- Create: `planner_database.py`
- Create: `planner_models.py`
- Create: `tests/test_planner_database.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `PlannerDatabase(path)`, `initialize()`, `transaction()`, `get_app_state()`, explicit schema version `1`.
- Tables: `user_places`, `favorites`, `routes`, `route_items`, `route_revisions`, `navigation_sessions`, `navigation_progress`, `app_state`.

- [ ] Write failing tests that initialize a temporary DB, assert schema version `1`, assert one autosaved Draft is created, and verify a route-item reorder plus revision insert rolls back together on injected failure.
- [ ] Run `python -m pytest tests/test_planner_database.py -q` and confirm RED due to missing module.
- [ ] Implement schema creation using one transaction, `PRAGMA foreign_keys=ON`, WAL mode, timestamps in UTC ISO-8601, and automatic `data/backups/` copy before any future migration of an existing DB.
- [ ] Run focused tests GREEN.
- [ ] Run `python -m pytest -q` and `node --test tests/*.mjs`.
- [ ] Commit `feat(planner): add sqlite persistence foundation`.

### Task 2: Route CRUD + revisions service

**Files:**
- Create: `route_service.py`
- Create: `tests/test_route_service.py`

**Interfaces:**
- Produces: `RouteService(db, graph_provider=None)` with `list_routes`, `get_active_route`, `create_route`, `rename_route`, `duplicate_route`, `add_item`, `move_item`, `remove_item`, `set_active`, `undo`, `redo`.
- Mutation result always contains `route_id`, `revision`, and canonical route payload.

- [ ] Write RED tests for Draft autosave, stable RouteItem IDs, add/move/remove, duplicate, active-route uniqueness, revision conflict, Undo/Redo of remove/reorder, and one-revision semantics for batch reorder.
- [ ] Implement atomic route mutations and command-style revision payloads (`add_item`, `move_item`, `remove_item`, `rename_route`, `optimize`, `reverse`).
- [ ] Ensure stale `expected_revision` raises `RouteRevisionConflict` without modifying DB.
- [ ] Run focused/full tests GREEN.
- [ ] Commit `feat(planner): add revisioned route service`.

### Task 3: Planner REST/SSE framework

**Files:**
- Create: `planner_events.py`
- Create: `planner_api.py`
- Modify: `server.py`
- Create: `tests/test_planner_api.py`

**Interfaces:**
- Produces REST routes under `/api/...` and SSE `/api/events`.
- `PlannerEventBus.publish(type, payload)` and subscriber queues.

- [ ] Write HTTP integration tests using an ephemeral `ThreadingHTTPServer` for routes create/list/active/add/move/remove/undo/redo and 409 conflict.
- [ ] Write an SSE test that subscribes, mutates a route, and receives `route.updated` with route ID/revision.
- [ ] Implement planner request dispatch without disrupting existing telemetry, road, tile, and navgraph endpoints.
- [ ] Publish events only after successful DB commit.
- [ ] Run Python/JS full suites GREEN.
- [ ] Commit `feat(planner): expose local rest and sse api`.

**Phase 1 gate:** fresh Python + JS suite, DB persistence across server restart, no changes to DRIVE output. Merge locally to `master` and remove phase worktree/branch.

---

## Phase 2 — Places Library, Favorites, My Places, Search Data

### Task 4: Built-in/curated catalog schemas and loader

**Files:**
- Create: `places_service.py`
- Create: `static/data/builtin_places.json`
- Create: `static/data/scenic_catalog.json`
- Create: `tests/test_places_service.py`

**Interfaces:**
- Produces `PlacesService(builtin_path, curated_path, db, graph_provider)` with `list_places`, `get_place`, `resolve_anchor`, `catalog_info`.
- Stable unified place result has `id`, `source`, `kind`, `name`, `aliases`, `category`, `subcategory`, `tags`, `position`, `navigation`, `surface`, `access`, `scenic_score`, `default_visible`, `featured`, `quality`.

- [ ] Write RED tests for source separation, stable IDs, recommended filtering, all-POI mode, place lookup, and malformed/duplicate ID rejection.
- [ ] Implement strict catalog loader and deterministic merged view with user places.
- [ ] Seed a minimal development catalog fixture only; final large catalog is produced in Phase 7.
- [ ] Run focused/full tests GREEN.
- [ ] Commit `feat(planner): add unified places catalog service`.

### Task 5: Favorites + My Places CRUD and WVAN snapping

**Files:**
- Modify: `places_service.py`
- Modify: `planner_api.py`
- Create: `tests/test_places_api.py`

**Interfaces:**
- REST: favorites add/delete, user-place create/update/delete.
- User-place mutation returns snapped `nav_anchor_point_id` and `nav_snap_distance` when graph is available.

- [ ] Write RED API/service tests for favoriting built-in/curated/user IDs, creating a user place, moving it and re-snapping, deleting an unreferenced place, and rejecting deletion when referenced by a saved route unless explicitly forced.
- [ ] Implement nearest graph point snapping in X/Z with no fabricated path; retain original selected coordinates.
- [ ] Publish `favorite.updated` and `place.updated` SSE events.
- [ ] Run all tests GREEN.
- [ ] Commit `feat(planner): add favorites and my places`.

### Task 6: Browser fuzzy search/filter engine

**Files:**
- Create: `static/planner/search.js`
- Create: `static/planner/library.js`
- Create: `tests/planner_search.test.mjs`

**Interfaces:**
- `buildSearchIndex(places)`; `searchPlaces(index, query, filters, sort)`.
- Filters include mode, quick flags, category, surface, access, source, quality; result includes dynamic category counts/chips.

- [ ] Write RED Node tests for aliases/tags, typo tolerance, combined filters, Recommended vs All, Favorites/Featured/My Places, dynamic counts, deterministic sort, and 3,000-place latency benchmark under a generous CI threshold.
- [ ] Implement normalized token index + lightweight edit-distance/prefix scoring with no runtime dependency.
- [ ] Preserve immutable search/filter state object suitable for back-navigation restoration.
- [ ] Run JS/Python suites GREEN.
- [ ] Commit `feat(planner): add fuzzy library search and filters`.

**Phase 2 gate:** catalog/service/API/search tests + existing suites; merge locally.

---

## Phase 3 — Directed Route Preview, Scenic Blocks, Reverse, Optimize

### Task 7: Shared directed graph runtime and route-preview service

**Files:**
- Modify/Create: `route_preview.py`
- Modify: `route_service.py`
- Create: `tests/test_route_preview.py`

**Interfaces:**
- `RoutePreviewService(graph)` exposes `preview(route, start_anchor=None)` returning `{revision, resolved, total_distance_m, legs, geometry}`.
- Each leg either has legal directed segment IDs/point IDs or explicit unresolved reason.

- [ ] Write RED tests against synthetic graph for one-way/no-right-turn preservation, ordinary stops, temporary waypoints, and unresolved legal path.
- [ ] Add real compiled-graph smoke test if `static/data/fh6_navgraph_v1.json.gz` exists.
- [ ] Implement graph loader/index and A*/Dijkstra over legal transitions only; do not import/consult legacy LabsGG routing.
- [ ] Cache anchor-to-anchor costs per graph/source revision.
- [ ] Run focused/full tests GREEN.
- [ ] Commit `feat(planner): add directed route preview service`.

### Task 8: Scenic Road/Loop atomic blocks

**Files:**
- Modify: `places_service.py`
- Modify: `route_preview.py`
- Create: `tests/test_scenic_blocks.py`

**Interfaces:**
- Scenic catalog entries contain mandatory forward/reverse or CW/CCW anchor sequences.
- Preview expands block internally while returning one top-level RouteItem summary.

- [ ] Write RED tests proving A* cannot shortcut a Scenic block, reverse direction uses reversed validated mandatory path, invalid internal path fails closed, and `reversible=true` requires both orientations to validate.
- [ ] Implement block resolver and fixed-path validation against compiled graph.
- [ ] Return approach/scenic/exit distances separately for details.
- [ ] Run suites GREEN.
- [ ] Commit `feat(planner): enforce atomic scenic route blocks`.

### Task 9: Reverse and constrained Optimize

**Files:**
- Modify: `route_service.py`
- Create: `route_optimizer.py`
- Create: `tests/test_route_optimizer.py`

**Interfaces:**
- `reverse_route(route_id, expected_revision, policy)`.
- `optimize_route(route_id, expected_revision, objective='fastest', keep_final=True, choose_orientation=True)`.

- [ ] Write RED tests for position locks, direction locks, final destination pinning, indivisible Scenic blocks, reversible orientation selection, reverse conflict reporting, and all-or-nothing failure when any optimized leg is unresolved.
- [ ] Implement exact DP optimizer for small N with orientation state and deterministic bounded heuristic fallback for larger N; use route-preview cost matrix.
- [ ] Persist optimize/reverse as single revision events containing before/after order/orientation.
- [ ] Run tests GREEN.
- [ ] Commit `feat(planner): add constrained reverse and optimizer`.

**Phase 3 gate:** graph legality + real graph smoke + all regressions; merge locally.

---

## Phase 4 — Planner UI Shell, Library, Map, Route Editor

### Task 10: Planner shell and API client

**Files:**
- Create: `static/planner/index.html`
- Create: `static/planner/planner.css`
- Create: `static/planner/api.js`
- Create: `static/planner/planner.js`
- Modify: `static/index.html`
- Modify: `static/app.js`
- Create: `tests/planner_ui_structure.test.mjs`

**Interfaces:**
- `/planner/` is served by existing server.
- DRIVE `PLAN ROUTE` focuses/reuses a named planner window.
- Planner client exposes one application state containing active route, route preview, places/search state, selected place/item, SSE status.

- [ ] Write RED structure tests for three-panel layout, header controls, PLAN button on DRIVE, separate-window reuse, status/autosave, and no dependency on `static/app.js` internals.
- [ ] Implement responsive shell with resizable/collapsible Library and Route panels, map center, saved widths in browser preference storage only.
- [ ] Implement REST/SSE client with optimistic revision handling.
- [ ] Run JS/full suites GREEN.
- [ ] Commit `feat(planner): add planner application shell`.

### Task 11: Library panel UX

**Files:**
- Modify: `static/planner/library.js`
- Modify: `static/planner/planner.js`
- Modify: `static/planner/planner.css`
- Create: `tests/planner_library_ui.test.mjs`

**Interfaces:**
- Always-visible search, quick chips, Recommended/All, advanced filters drawer, selected filter chips, compact virtualized list, detail view.

- [ ] Write RED DOM-independent rendering/state tests for filter chips, counts, add-to-route indicator, details/back preserving query/filter/sort/scroll, and keyboard search navigation.
- [ ] Implement virtualized list and detail state without multi-select/Near Me/Search This Area.
- [ ] Add keyboard shortcuts Ctrl+F, arrows, Enter, Ctrl+Enter, Esc.
- [ ] Run suites GREEN.
- [ ] Commit `feat(planner): build searchable places library ui`.

### Task 12: Planner map interactions

**Files:**
- Create: `static/planner/map.js`
- Modify: `static/planner/planner.js`
- Modify: `static/planner/planner.css`
- Create: `tests/planner_map.test.mjs`

**Interfaces:**
- Uses same tile/calibration/map projection approach as DRIVE but separate state/module.
- Single click selects; double click adds Temporary Waypoint; right click exposes set destination/add waypoint/add via/save; Shift+click quick-adds.

- [ ] Write RED tests for click semantics, route-marker independence from Library filters, marker numbering, cluster eligibility rules, selected/favorite/featured visual priority model, and temporary waypoint creation.
- [ ] Implement Canvas/SVG layers or reuse map primitives without coupling to DRIVE DOM.
- [ ] Implement context menu and draggable My Place marker with API re-snap.
- [ ] Run suites GREEN.
- [ ] Commit `feat(planner): add interactive planner map`.

### Task 13: Route editor panel

**Files:**
- Create: `static/planner/route_editor.js`
- Create: `static/planner/history.js`
- Modify: `static/planner/planner.js`
- Create: `tests/planner_route_editor.test.mjs`

**Interfaces:**
- Compact RouteItems with one expanded row; drag handle + Up/Down + Remove; locks/direction; Optimize/Reverse; Start Navigation gate.

- [ ] Write RED state tests for drag preview/no A* until drop, Up/Down, remove+Undo toast, expanded Scenic/point details, lock controls, unresolved-leg presentation, Start disabled, and stale preview revision discard.
- [ ] Implement optimistic operations, route-calculation status, route totals/leg stats, and one expanded item at a time.
- [ ] Implement Ctrl+Z/Ctrl+Y/Delete shortcuts and confirmation only for large destructive actions.
- [ ] Run suites GREEN.
- [ ] Commit `feat(planner): add route editor and history ui`.

**Phase 4 gate:** complete Planner shell core-flow Node tests + existing DRIVE regression; merge locally.

---

## Phase 5 — Navigation Sessions and Live PLAN ↔ DRIVE

### Task 14: Navigation session backend

**Files:**
- Create: `navigation_service.py`
- Modify: `planner_api.py`
- Create: `tests/test_navigation_service.py`

**Interfaces:**
- Start/stop/skip/previous session; session progress independent from saved route item state.
- Automatic completion helper accepts current match/route progress and returns transition when within 50m and on correct legal route leg.

- [ ] Write RED tests for start validation, independent repeat sessions, skip/previous, current-item deletion during live edit, new future item insertion, and 50m+WVAN-leg completion gate.
- [ ] Implement session/progress transactions and publish `navigation.updated`.
- [ ] Reject start if preview unresolved.
- [ ] Run suites GREEN.
- [ ] Commit `feat(planner): add navigation sessions and progress`.

### Task 15: DRIVE consumes Active Route revisions

**Files:**
- Modify: `static/app.js`
- Modify: `static/index.html`
- Create: `tests/planner_drive_sync.test.mjs`

**Interfaces:**
- DRIVE subscribes to SSE route/session events, loads active route/session, uses Planner route target sequence while preserving existing map matcher/reroute.

- [ ] Write RED architecture tests that PLAN changes trigger active route reload, already visited items remain completed, deleting current target selects next applicable item, and no legacy shortestPath fallback is introduced.
- [ ] Implement `МАРШРУТ ОБНОВЛЁН`, `Skip stop`, `Previous stop`, active-route name/progress, and focus/open behavior.
- [ ] Preserve existing missed-turn `ПЕРЕСТРАИВАЮ МАРШРУТ…` semantics distinct from user-plan update.
- [ ] Run all suites GREEN.
- [ ] Commit `feat(planner): synchronize active route with drive`.

**Phase 5 gate:** API + browser flow + DRIVE regression, merge locally.

---

## Phase 6 — Backup, Route Import/Export, Diagnostics

### Task 16: User backup and route formats

**Files:**
- Create: `planner_io.py`
- Modify: `planner_api.py`
- Create: `tests/test_planner_io.py`

**Interfaces:**
- Versioned full backup JSON and `.fh6route` individual route format.
- Built-in content referenced by stable ID; unresolved imports reported but non-destructive.

- [ ] Write RED tests for export/import round trip, stable-ID references, missing built-in ID warnings, user-place inclusion, duplicate-safe import, and unsupported format version rejection.
- [ ] Implement APIs and route/user-data export controls in Planner menu.
- [ ] Run suites GREEN.
- [ ] Commit `feat(planner): add backup and route import export`.

### Task 17: Diagnostics and validation surfaces

**Files:**
- Create: `catalog_validator.py`
- Modify: `planner_api.py`
- Modify: `static/planner/planner.js`
- Create: `tests/test_catalog_validator.py`

**Interfaces:**
- Validator rejects duplicate IDs/bad coordinates/broken anchors/scenic paths.
- Advanced Planner options can show navigation anchors/directed graph without changing route authority.

- [ ] Write RED validation tests for every release-time catalog failure category in the spec.
- [ ] Implement validator and diagnostic API metadata.
- [ ] Add advanced UI toggles for anchors/graph.
- [ ] Run suites GREEN.
- [ ] Commit `feat(planner): add catalog validation and diagnostics`.

**Phase 6 gate:** full tests, merge locally.

---

## Phase 7 — Internet Catalog Import and Curated Seed

### Task 18: Internet source research and raw-source adapters

**Files:**
- Create: `tools/places_import/__init__.py`
- Create: `tools/places_import/models.py`
- Create: `tools/places_import/normalize.py`
- Create: `tools/places_import/dedupe.py`
- Create: `tools/places_import/build_catalog.py`
- Create source-adapter modules for each selected public source whose terms/access allow factual extraction.
- Create: `tests/test_places_import.py`

**Interfaces:**
- Input adapters emit `RawPlace(provider, source_id, name, category, x/y or map coordinates, aliases, tags, provenance)`.
- Builder emits only factual names/categories/positions plus our own metadata; it does not copy third-party descriptions/images.

- [ ] Research current FH6 public maps/guides and select at least two independent factual sources where practical; record source names and retrieval date in build metadata.
- [ ] Write fixtures/snapshot tests for adapters rather than making tests depend on live internet.
- [ ] Implement normalization/deduplication by provider ID, normalized name/category, and coordinate proximity; preserve aliases/provenance.
- [ ] Add deterministic map-coordinate→game-coordinate transform adapters only where calibration is proven; otherwise keep records out of runtime catalog rather than guessing.
- [ ] Run importer tests GREEN.
- [ ] Commit `feat(catalog): add build time internet importer`.

### Task 19: Build large official catalog + curated candidate layer

**Files:**
- Generate/modify: `static/data/builtin_places.json`
- Generate/modify: `static/data/scenic_catalog.json`
- Create: `tools/places_import/curate.py`
- Create: `tests/test_catalog_scale.py`

**Interfaces:**
- Target total official/community factual POIs: 700+ when source data supports it.
- Recommended visible set target: approximately 150–250 destinations, selected by category/confidence/utility rules.

- [ ] Run source adapters and collect all available factual POIs.
- [ ] Snap valid candidate destinations to compiled WVAN graph; calculate snap distance and route reachability confidence.
- [ ] Apply `verified/reviewed/probable/unverified`, default-visible, featured, surface/access/category rules conservatively.
- [ ] Seed Navigator Curated Scenic Places/Roads/Loops only where an internet/community candidate plus graph geometry provides enough evidence; leave uncertain candidates out rather than inventing them.
- [ ] Run catalog validator; assert unique stable IDs, valid anchors, and catalog scale/Recommended-set bounds when available source count permits.
- [ ] Commit `data(catalog): populate fh6 places library`.

**Phase 7 gate:** importer snapshots + catalog validator + Planner search performance + real WVAN graph; merge locally.

---

## Phase 8 — End-to-End Acceptance, Documentation, Release

### Task 20: Acceptance browser/API scenarios

**Files:**
- Create: `tests/planner_acceptance.test.mjs`
- Create/modify API scenario tests.

- [ ] Encode acceptance flows: Search→Add→Add→reorder→Start; map double-click→Undo; Optimize→Undo; live edit while DRIVE active; Draft survives reload/server restart; unresolved path disables Start.
- [ ] Run full Python/JS suites.
- [ ] Run real WVAN graph validation and catalog validation.
- [ ] Commit `test(planner): cover planner v1 acceptance flows`.

### Task 21: User documentation

**Files:**
- Modify: `README_RU.md`
- Modify: `HOW_TO_START.txt`
- Create: `PLANNER_RU.md`

- [ ] Document DRIVE→PLAN workflow, search/filters, My Places, temporary waypoints, Scenic blocks, locks, Optimize/Reverse, autosave/Undo, Saved Routes, Start Navigation, import/export, SQLite backup location, and fail-closed routing.
- [ ] Document explicit v1 non-goals without promising runtime internet/cloud functionality.
- [ ] Commit `docs(planner): add route planner user guide`.

### Task 22: Clean release gate and packaging

**Files:** release artifact only.

- [ ] Run `python -m pytest -q`.
- [ ] Run `node --test tests/*.mjs`.
- [ ] Run catalog validator against shipped JSON.
- [ ] Validate embedded `fh6_navgraph_v1.json.gz` and Scenic blocks.
- [ ] Start server on an ephemeral port; smoke `/`, `/planner/`, `/api/navgraph`, `/api/places`, `/api/routes/active`, `/api/events` connection.
- [ ] Confirm `git status` clean and `git ls-files` contains no raw `.nav/.owt/.oww/.owbs` assets.
- [ ] Build `FH6_Scenic_Navigator_v1.15_ROUTE_PLANNER.zip`, excluding `.git`, worktrees, caches, user `data/navigator.db`, test temporary files, and raw game assets.
- [ ] Unpack ZIP into a clean directory and repeat Python/JS/catalog/server smoke matrix from the unpacked release.
- [ ] Merge final phase locally to `master`, remove worktree/branch, and provide the verified ZIP.

---

## Self-Review Mapping

- Spec §§1–2 → Phases 1, 4, 5.
- §§3–6 → Phases 2, 7.
- §§7–10 → Phases 3–4.
- §§11–14 → Phases 3, 5.
- §§15–16 → Phase 1.
- §§17–20 → Phase 4.
- §§21–23 → Phases 6–7.
- §§24–25 → every phase gate + Phase 8.
- §26 non-goals are enforced in Global Constraints.
- §27 acceptance is explicitly encoded by Phase 8 Task 20.

No implementation step may substitute legacy LabsGG routing for an unresolved WVAN leg, and no catalog build may invent coordinates, POIs, Scenic Roads, or source provenance absent supporting data.
