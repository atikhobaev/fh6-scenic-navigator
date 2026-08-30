# FH6 Scenic Navigator v1.16 Map-First Planner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the existing v1.15 Route Planner into the approved map-first v1.16 Planner with complete layer filters/search, on-map popovers, a read-only built-in Grand Tour route with edit-on-copy, and offline-local image/community catalog support while preserving Directed WVAN routing.

**Architecture:** Keep the existing Python local backend and modular browser planner. Add focused frontend modules for layer registry and popovers, extend `PlannerMap` rather than moving logic into `planner.js`, and represent built-in routes in `RouteService` as virtual read-only route objects that are copied into SQLite only on first structural edit. Extend `PlacesService` with a third read-only community catalog and strict local-image validation; the build-time importer may retain unresolved source evidence but only emits runtime places with proven coordinates and valid WVAN anchors.

**Tech Stack:** Python 3.11 standard library + SQLite, Node.js ES modules + node:test, existing Directed WVAN graph JSON.gz, vanilla HTML/CSS/SVG.

**Spec:** `docs/superpowers/specs/2026-08-29-planner-map-first-ui-redesign-design.md`

## Global Constraints

- Directed WVAN remains the authoritative router; no legacy bidirectional `shortestPath` fallback is introduced.
- Runtime Planner UI must not depend on ForzaLabsGG or ForzaHorizon.app network access.
- All useful marker categories stay available; Recommended starts calm and is persisted locally.
- Search spans the full catalog, including hidden layers.
- Active route markers/geometry and the selected marker never disappear because of layer filters or clustering.
- Place details render as an anchored map popover, never a separate detail page.
- Built-in `Grand Tour Japan` is immutable and starts directly; any structural edit transparently creates an editable copy.
- Runtime place image paths must be local `/media/places/...` paths; remote HTTP(S) image URLs are rejected.
- Community records without proven coordinates stay evidence-only and are never released into the routable runtime catalog.
- Existing Python/JS regression suites must remain green; final release must pass catalog validation and ZIP hygiene checks.

---

### Task 1: Map-first layer registry and filter state

**Files:**
- Create: `static/planner/layers.js`
- Modify: `static/planner/search.js`
- Modify: `static/planner/library.js`
- Test: `tests/planner_layers.test.mjs`

**Interfaces:**
- Produces `LAYER_GROUPS`, `LAYER_REGISTRY`, `recommendedLayerIds()`, `normalizeLayerState()`, `layerForPlace(place)`, and `isPlaceVisible(place, layerState, context)`.
- `searchPlaces` gains `respectLayers`/full-catalog search behavior without hiding matches just because the map layer is off.

- [ ] **Step 1:** Write tests proving full taxonomy, Recommended preset, all/none/reset, persisted normalization, and route/selected visibility overrides.
- [ ] **Step 2:** Run `node --test tests/planner_layers.test.mjs` and verify it fails because `layers.js` does not exist.
- [ ] **Step 3:** Implement `layers.js` and minimal search/library state changes.
- [ ] **Step 4:** Run targeted and existing search/library tests until green.
- [ ] **Step 5:** Commit `feat(planner): add map layer registry`.

### Task 2: Marker hierarchy, clustering exclusions, and on-map popover

**Files:**
- Create: `static/planner/popover.js`
- Modify: `static/planner/map.js`
- Test: `tests/planner_markers_popover.test.mjs`

**Interfaces:**
- `PlannerMap.setData` accepts `layerState`, `searchRevealId`, and `popover` selection context.
- `clusterMarkers` respects `clusterable=false`.
- `buildPlacePopoverModel(place, inRoute)` produces text/actions and a local-only image path.

- [ ] **Step 1:** Write failing tests for cluster exclusions, marker-layer mapping, local-image-only popover, and compact no-image popover.
- [ ] **Step 2:** Run tests and observe expected failures.
- [ ] **Step 3:** Implement popover model and map marker rendering/hierarchy.
- [ ] **Step 4:** Run targeted map/popover tests plus `planner_map.test.mjs`.
- [ ] **Step 5:** Commit `feat(planner): add layered markers and map popovers`.

### Task 3: Replace three-panel library UI with map-first shell

**Files:**
- Modify: `static/planner/index.html`
- Modify: `static/planner/planner.css`
- Modify: `static/planner/planner.js`
- Test: `tests/planner_map_first_ui.test.mjs`

**Interfaces:**
- Top bar owns global `#placeSearch`.
- Left `#libraryPanel` becomes `MAP FILTERS` rail with quick chips, grouped layer controls, surfaces/sources, and bulk actions.
- `#placePopover` is map-anchored; `#placeDetails` no longer exists.
- Existing route rail and route editing API remain unchanged.

- [ ] **Step 1:** Write structure tests for map-first DOM and absence of old detail/list default UX.
- [ ] **Step 2:** Run test and verify failure against v1.15 DOM.
- [ ] **Step 3:** Rewrite HTML/CSS shell and bind Planner controller to layers/search/popover while retaining route/import/export/diagnostics/add-place flows.
- [ ] **Step 4:** Run all Planner UI JS tests and fix regressions.
- [ ] **Step 5:** Commit `feat(planner): switch planner to map-first UX`.

### Task 4: Built-in Grand Tour route + edit-on-copy

**Files:**
- Create: `builtin_routes.py`
- Modify: `route_service.py`
- Modify: `planner_api.py`
- Modify: `navigation_service.py` only if needed for virtual-route lookup compatibility.
- Modify: `static/planner/api.js`
- Modify: `static/planner/planner.js`
- Test: `tests/test_builtin_routes.py`
- Test: `tests/planner_builtin_route_ui.test.mjs`

**Interfaces:**
- Stable built-in route ID: `builtin.grand_tour_japan`.
- Built-in route has `read_only=true`, deterministic stable item IDs, and resolved place/temporary world coordinates derived from `static/route.json`/existing calibration.
- `RouteService.ensure_editable_route(route_id)` returns `(route_id, copied)` and activates an editable `Grand Tour Japan — Copy` when mutating a built-in route.
- `GET /api/routes` returns `built_in` and user routes; `GET /api/routes/:id`/preview/start accept built-ins.

- [ ] **Step 1:** Write failing backend tests for listing/opening/previewing built-in route, no SQLite row, direct navigation start, and edit-on-copy.
- [ ] **Step 2:** Run targeted tests and verify failures.
- [ ] **Step 3:** Implement built-in route provider and RouteService/API integration.
- [ ] **Step 4:** Add JS tests for Built-in/Saved grouping and read-only edit-on-copy UX; implement client support.
- [ ] **Step 5:** Run Python + Planner JS suites and commit `feat(planner): add built-in Grand Tour route`.

### Task 5: Community catalog and offline-local images

**Files:**
- Create: `static/data/community_places.json`
- Create: `static/data/community_evidence.json`
- Create: `scripts/import_forzahorizon_community.py`
- Create: `static/media/places/community/.gitkeep`
- Modify: `places_service.py`
- Modify: `server.py`
- Modify: `catalog_validator.py`
- Test: `tests/test_community_places.py`
- Test: `tests/test_forzahorizon_importer.py`

**Interfaces:**
- `PlacesService(..., community_path=None, media_root=None)` loads optional source=`community` catalog.
- Static place validation accepts optional `image`, `image_thumb`, `image_attribution`, `image_source`, `external_source_id`, `popularity` but rejects remote runtime image paths.
- `/media/places/...` is served as a local static asset path.
- Importer normalizes source evidence, derives deterministic filenames/checksums, and emits runtime records only when coordinates are explicitly supplied/proven and snapping succeeds.

- [ ] **Step 1:** Write failing validation/importer tests including rejection of remote image URLs and exclusion of coordinate-less evidence.
- [ ] **Step 2:** Run targeted tests and verify failures.
- [ ] **Step 3:** Implement service/server/validator/importer and empty runtime community catalog + evidence snapshot.
- [ ] **Step 4:** Add at least one bundled local placeholder-free image-backed verified place only if a proven coordinate/image pairing exists; otherwise keep runtime catalog valid and document evidence-only limitation rather than fabricate coordinates.
- [ ] **Step 5:** Run catalog and importer tests; commit `feat(planner): add offline community catalog pipeline`.

### Task 6: Release polish, regression, and package

**Files:**
- Modify: `README_RU.md`
- Modify: `PLANNER_RU.md`
- Modify: `HOW_TO_START.txt` if version text exists.
- Modify: any version/banner constants.
- Test: all suites + clean-package smoke.

**Interfaces:**
- Release label `v1.16 MAP-FIRST PLANNER`.
- ZIP root directory `FH6_Scenic_Navigator_v1.16_MAP_FIRST_PLANNER/`.

- [ ] **Step 1:** Update docs/version text and add map-first/built-in/community behavior notes.
- [ ] **Step 2:** Run `python -m pytest -q`.
- [ ] **Step 3:** Run `node --test tests/*.mjs`.
- [ ] **Step 4:** Run `python catalog_validator.py`, `git diff --check`, and raw game asset hygiene checks.
- [ ] **Step 5:** Verify no runtime third-party URL dependencies in Planner and no generated DB/cache/pyc files in release.
- [ ] **Step 6:** Commit `release: prepare v1.16 map-first planner`.
- [ ] **Step 7:** Use finishing-a-development-branch + verification-before-completion, merge feature branch into local `master`, rerun full verification on merged master, then create final ZIP.
