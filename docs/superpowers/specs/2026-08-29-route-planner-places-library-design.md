# FH6 Route Planner + Places Library Design

**Status:** Approved design consolidation, pending final user review before implementation planning.

**Product:** FH6 Scenic Navigator v1.14+  
**Scope:** Local desktop-first Route Planner + Places Library only.  
**Explicitly deferred:** cloud/accounts/community sharing, Cloud/Bridge, multilingual UI, full mobile Planner, Near Me, Search This Area, community ratings, runtime web scraping, Scenic optimization profile, Library multi-select.

---

## 1. Product Direction

The existing DRIVE experience remains the minimal navigation screen. A new PLAN experience is added at `/planner` for route construction and library management.

The application has two complementary modes:

- **DRIVE** — the existing low-distraction navigation UI using the directed WVAN graph.
- **PLAN** — a dedicated route-planning workspace with a Places Library, map, and route editor.

The PLAN page is a normal route inside the same local web application, but the DRIVE button **PLAN ROUTE** opens/focuses it in a separate browser window by default. If it is already open, the existing window is focused instead of spawning duplicates. The page remains usable as an ordinary browser tab if opened directly.

The design must remain compatible with a future multilingual and cloud-backed product, but those features are not part of Planner v1.

### 1.1 Primary layout

Desktop-first three-panel workspace:

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ PLAN · Active Route · Autosaved        Undo / Redo         DRIVE status      │
├────────────────────┬──────────────────────────────────┬───────────────────────┤
│ PLACES LIBRARY     │                                  │ CURRENT ROUTE         │
│                    │                                  │                       │
│ search             │               MAP                │ Current car           │
│ quick filters      │                                  │ route items           │
│ filter chips       │                                  │ drag / arrows / menu  │
│ place list         │                                  │                       │
│                    │                                  │ Optimize / Reverse    │
│                    │                                  │ Start Navigation      │
└────────────────────┴──────────────────────────────────┴───────────────────────┘
```

Target desktop widths:

- Library: 320–380 px.
- Map: flexible remaining space.
- Route: 340–420 px.

Side panels are resizable and collapsible. Their widths/collapsed states are persisted locally.

Below approximately 1050 px, Library and Route become overlay drawers around the map. A full touch/mobile Planner is not part of v1.

### 1.2 Core UX principle

The system may be technically powerful, but the basic user journey must stay simple:

```text
Search → + Route → Search → + Route → reorder if needed → Start Navigation
```

Advanced concepts such as VIA points, Scenic blocks, locks, direction constraints, revisions, and WVAN anchors must not obstruct this flow.

---

## 2. Active Route, Drafts, and Saved Routes

The application has exactly **one Active Route** at a time. DRIVE never chooses a route independently; it always consumes the server's active route.

In addition, the user can maintain Saved Routes.

### 2.1 Draft behavior

An unsaved route is still a real persistent Route object:

- default name: `Draft Route`;
- `is_draft = true`;
- autosaved to SQLite after every completed edit;
- survives page refresh, browser close, and server restart.

`Save as...` converts a Draft into a named Saved Route. A new empty Draft is created only when needed.

### 2.2 Top bar

The PLAN header contains:

- Active Route name, inline-editable.
- Autosave state: `Saving…` → `Autosaved`.
- Saved Routes menu.
- New route.
- Duplicate route.
- Undo / Redo.
- More menu for less frequent actions.
- DRIVE connection/open state.

Saved Routes menu supports:

- Open.
- Rename.
- Duplicate.
- Delete.
- Save current as…

Recent routes are surfaced separately from the full saved list.

### 2.3 Start Navigation

`START NAVIGATION` is enabled only when:

- at least one route item exists;
- all required anchors are valid;
- every required directed leg resolves legally through the WVAN graph.

Starting navigation:

1. Creates a Navigation Session.
2. Initializes route progress.
3. Map-matches the current vehicle.
4. Builds the active yellow leg.
5. Opens/focuses DRIVE.
6. Keeps PLAN open and editable.

Once active, Planner shows `NAVIGATION ACTIVE` with an `OPEN DRIVE` action.

---

## 3. Places Library Architecture

The Places Library presents a unified interface over three independent sources:

1. **Official Game Places** — built at release time from available public FH6 location datasets.
2. **Navigator Curated** — our own Scenic Places, Scenic Roads, Scenic Loops, and Collections.
3. **My Places** — user-created data stored in SQLite.

The user should not need to know which storage mechanism owns a place. Source is primarily used for filtering and maintenance.

### 3.1 Physical data separation

```text
static/data/builtin_places.json    # read-only game catalog
static/data/scenic_catalog.json    # read-only curated catalog
data/navigator.db                  # user-owned data only
```

Updating built-in or curated catalogs must never overwrite user data.

### 3.2 Place model

A point/area entity contains at minimum:

```text
id
source                  game | curated | user
kind                    point | area
name
aliases[]
position_x/y/z
nav_anchor_point_id
nav_snap_distance
category
subcategory
tags[]
region
surface                 asphalt | dirt | mixed | unknown
access                  easy | normal | offroad | unknown
scenic_score
featured
default_visible
quality                 verified | reviewed | probable | unverified
source_metadata
```

Stable IDs must not depend on display names. Examples:

```text
builtin.game.house.casa_bella
builtin.game.landmark.daikoku_parking_area
curated.place.volcano_overlook
user.<uuid>
```

Favorites and routes reference IDs rather than copying built-in records.

### 3.3 Recommended vs full catalog

The release target is a comprehensive library on the order of 700+ total game/community-derived objects where available, while the default user-facing catalog remains curated to roughly 150–250 useful destinations.

Library mode:

```text
Recommended
All game POIs
```

`Recommended` uses `default_visible=true`; full mode removes that restriction.

Events, PR stunts, collectibles, and other large categories remain discoverable without overwhelming the default view.

### 3.4 Categories

Top-level information architecture:

```text
FAVORITES

DISCOVER
  Featured
  Scenic Places
  Scenic Roads
  Scenic Loops
  Collections

GAME
  Houses
  Landmarks
  Festival Sites
  Events
  PR Stunts
  Collectibles

MY LIBRARY
  My Places
```

Subcategories expand only after selecting a relevant parent category. The UI must not expose an enormous tree by default.

### 3.5 Search

Search is always visible and updates results while typing.

Indexed fields:

- name;
- aliases;
- category/subcategory;
- tags;
- region;
- collection names.

The client builds a compact normalized search index after catalog load. Matching is fuzzy enough to tolerate small spelling mistakes. Search and filters compose rather than replacing one another.

Target perceived response for typing/filtering: under roughly 100–150 ms.

### 3.6 Filtering

Always-visible quick filters:

- Favorites.
- Featured.
- My Places.
- Recommended / All game POIs selector.

Advanced `Filters` panel:

- Category.
- Surface.
- Access.
- Source.
- Quality.

Active filters appear as removable chips below the search box, with `Clear all`.

Category result counts update with the current search/filter state.

Deferred filters: Near Me and Search This Area.

### 3.7 Sorting v1

- Recommended.
- Name A–Z.
- Most scenic.
- Recently used.

Distance-from-car sorting is deferred with Near Me.

### 3.8 Place cards

Compact result card:

```text
★ Hakone Nanamagari
  Scenic Road · Asphalt · ★★★★★

                              [+]
```

Behaviors:

- hover highlights the corresponding map entity;
- click selects the place and opens details in the Library panel;
- `+` adds directly to the Active Route without opening details;
- already-used single-place items display `In route` rather than a misleading add state where appropriate.

Library details are in-panel, not a modal. Returning restores query, filters, sorting, selection, and scroll position.

### 3.9 Marker clustering

Only filtered non-route POIs are clustered at distant zoom levels.

Never cluster:

- Route markers.
- Selected marker.
- Highlighted Scenic geometry.

Marker visual priority:

1. Active Route.
2. Selected Place.
3. Favorites.
4. Featured.
5. Normal Places.
6. Events.
7. Collectibles.

Library filters must never hide Active Route geometry or Route markers.

---

## 4. Navigator Curated Content

The curated catalog is a first-class product layer, separate from official game POIs.

### 4.1 Scenic Place

A destination selected for driving/visual interest. May contain:

- surface;
- access difficulty;
- scenic score;
- tags;
- short original description.

### 4.2 Scenic Road

A Scenic Road is a route-building block rather than a single POI.

```text
id
type = road
name
entry_anchor
exit_anchor
forward_via_anchors[]
reverse_via_anchors[]
display_geometry[]
surface
distance
scenic_score
tags[]
reversible
recommended_direction
quality
```

When added to a route, the internal directed path is mandatory. A* can choose the approach to the entry and the continuation from the exit, but must not cut through or replace the chosen Scenic Road.

### 4.3 Scenic Loop

Equivalent concept for a loop:

- clockwise anchors;
- counter-clockwise anchors;
- recommended direction;
- optional reverse direction if validated.

The user sees one Route Item rather than the internal anchors.

### 4.4 Collections

Collections group Places/Roads/Loops for discovery, e.g. `Best Mountain Drives`. A Collection is not itself inserted into a route in v1.

### 4.5 Curated quality

Candidate content may exist as probable/draft build data, but the normal user catalog shows only content meeting the release quality rules.

---

## 5. Build-Time Internet Importer

The user is not responsible for populating the official catalog. We build it from available internet data before releases.

The Navigator must **not scrape third-party websites at runtime**.

### 5.1 Pipeline

```text
Internet/public FH6 location sources
        ↓
raw imports
        ↓
normalization
        ↓
deduplication
        ↓
coordinate conversion
        ↓
WVAN snapping
        ↓
validation/confidence
        ↓
builtin_places.json
```

### 5.2 Normalization

Normalize:

- source IDs;
- names/aliases;
- categories;
- coordinate representations;
- tags where supportable.

Do not copy third-party prose descriptions or imagery into the product. The catalog should retain factual/structural data needed for navigation and search, with original curated copy where descriptions are needed.

### 5.3 Deduplication

Deduplication considers, in order:

1. explicit source ID mapping;
2. normalized name/aliases;
3. category compatibility;
4. coordinate proximity.

Duplicates across providers become one stable Place with multiple provenance entries.

### 5.4 Provenance and confidence

Build metadata retains provider/source identifiers and import timestamps.

Quality states:

- **verified** — strong multi-source agreement and valid WVAN anchor/path.
- **reviewed** — trusted curated/reviewed record.
- **probable** — one suitable source plus plausible WVAN match.
- **unverified** — suspicious/incomplete; hidden by default.

### 5.5 WVAN anchor

The displayed POI position and navigation target are intentionally separate:

```text
real place marker
       │ snap distance
       ▼
WVAN navigation anchor
```

Routing targets the legal `nav_anchor_point_id`; the map continues to show the actual place coordinates.

Build validation flags excessive snap distances and unreachable anchors.

### 5.6 Catalog versioning

Each release catalog includes:

```text
schema_version
catalog_version
```

Built-in and curated catalogs are versioned independently from application code and user SQLite schema.

---

## 6. My Places

Users can add and remove their own places without modifying built-in catalogs.

### 6.1 Creation methods

`+ ADD PLACE` supports:

- Pick on map.
- Current car position.
- Enter coordinates (advanced).

Map pick shows an editable marker and compact form:

- name;
- category;
- notes;
- favorite toggle.

The marker can be moved before save.

Moving an existing user place re-runs WVAN snapping.

If snapping is unusually far away, saving is allowed but the UI warns that navigation will stop at the nearest reachable road.

### 6.2 User Place persistence

`user_places` stores:

```text
id
name
category
notes
x/y/z
nav_anchor_point_id
nav_snap_distance
created_at
updated_at
```

---

## 7. Map Interaction Model

Approved pointer semantics:

- **Single click empty map:** select/cursor only; no route mutation.
- **Single click POI:** select POI and show compact/detail UI.
- **Double click map:** add a Temporary Waypoint to the end of Active Route.
- **Right click map:** Set as destination / Add waypoint / Add VIA / Save to My Places.
- **Shift+click:** rapid route-building mode; each click adds the next route item/waypoint.

Advanced map context may show X/Z coordinates unobtrusively.

Map and Library hover/selection states are synchronized.

---

## 8. Route Item Model

The Route consists of top-level Route Items, not a raw coordinate array.

Supported v1 item types:

```text
place
temporary
scenic_road
scenic_loop
```

Points also support the semantic role:

```text
stop
via
```

VIA is part of the data model immediately, even if initially exposed only through advanced actions and Scenic blocks.

Each Route Item has a stable item ID independent from its list position.

### 8.1 Route Item persisted fields

```text
id
route_id
position
type
place_id? 
temporary_x/y/z?
nav_anchor_point_id?
scenic_block_id?
direction?
stop_type
position_locked
direction_locked
```

Route progress status is session-specific rather than permanently stored on the Saved Route.

### 8.2 Temporary Waypoint

Double-click or context-menu addition creates a temporary Route Item without adding it to the Places Library.

Default labels: `Waypoint 1`, `Waypoint 2`, etc.

Details allow:

- Rename.
- Save to My Places.
- Convert to VIA.
- Show on map.
- Remove.

Saving to My Places preserves the existing Route Item identity and attaches the new `place_id`.

---

## 9. Current Route Panel

Default presentation is compact. Only one selected item expands to show detailed controls.

Compact example:

```text
1  Daikoku Parking Area
   Stop · 12.4 km                 ↑ ↓ ×

2  Hakone Mountain Road      🔒
   Scenic Road · 24.7 km · A→B   ↑ ↓ ×
```

Features:

- drag handle;
- drag-and-drop reorder;
- explicit Up / Down controls;
- remove;
- per-leg distance/status;
- selected-item expansion;
- lock indicators;
- unresolved-leg warnings.

During drag, marker numbering can preview the new order, but A* does not recalculate until drop.

Drop zones must be generous and explicit.

### 9.1 Expanded Scenic block

Shows:

- total distance/time estimate where available;
- surface/scenic metadata;
- direction;
- reverse direction action;
- Lock position;
- Lock direction;
- internal VIA count (not raw list by default);
- Show on map;
- Duplicate;
- Remove.

### 9.2 Expanded point

Shows:

- place/waypoint type;
- snap distance where useful;
- Show on map;
- Save to Library for temporary points;
- Convert to VIA;
- Remove.

### 9.3 Remove and Undo

Routine removal has no confirmation dialog. It creates one revision and shows an Undo toast. Undo restores the same Route Item ID and position.

---

## 10. Locks, Reverse, and Optimize

### 10.1 Position lock

`position_locked=true` prevents Optimize from moving the item.

Manual drag/drop is still allowed, but explicitly moving a position-locked item removes that position lock after a warning/clear affordance rather than silently violating it.

### 10.2 Direction lock

For reversible Scenic Roads/Loops, `direction_locked=true` prevents Optimize from changing orientation.

### 10.3 Reverse entire route

`Current car` remains the start.

Reverse transforms:

```text
CAR → A → Road A→B → C → Loop CW → D
```

into:

```text
CAR → D → Loop CCW → C → Road B→A → A
```

where the blocks are reversible.

If a direction lock prevents a complete reverse, Planner must not silently override it. It presents:

- Unlock and reverse.
- Keep direction and reverse order.
- Cancel.

### 10.4 Optimize

Planner v1 exposes:

```text
Fastest
Shortest
```

The future Scenic profile is reserved but hidden until quality scenic weights exist.

Options:

- Keep final destination.
- Respect locked items.
- Keep Scenic blocks intact.
- Choose best direction for reversible blocks.

Optimizer operates on top-level Route Items. It never breaks Scenic blocks into internal VIA points.

A reversible Scenic block contributes alternative orientation costs to the optimization problem.

Optimize is atomic and fail-closed: a candidate order is committed only after every directed leg validates. Failure leaves the original Route untouched.

Optimize/Reverse each create one undoable revision, not one revision per internal mutation.

---

## 11. Directed Route Preview

Each completed Route edit creates a new monotonic route revision and triggers preview calculation.

```text
Route revision N
    ↓
resolve Route Items
    ↓
expand mandatory Scenic anchors
    ↓
directed WVAN routing
    ↓
validate every leg
    ↓
RoutePreview(revision=N)
```

If revision N+1 exists before the old preview completes, the revision-N result is ignored/cancelled.

### 11.1 Scenic block enforcement

For a Scenic Road:

```text
previous item
  → free directed A* → entry
  → fixed validated scenic directed path
  → free directed A* → next item
```

The router must never shorten away the required Scenic geometry.

### 11.2 Unresolved leg

If no legal directed path exists:

- route item/leg shows `Route unavailable`;
- map keeps all valid geometry;
- problem endpoints may be connected with a thin red dotted straight indicator, explicitly not a route;
- `START NAVIGATION` is disabled;
- no fallback to legacy LabsGG shortestPath is permitted.

Fail-closed behavior applies to Preview, Optimize, Scenic blocks, DRIVE, and rerouting.

### 11.3 Statistics

Each Route Item displays the leg distance from the previous top-level item. Scenic details may break this into approach distance + Scenic block distance.

Total route distance/time is shown at the top of the route panel where reliably computable.

---

## 12. Live PLAN ↔ DRIVE Synchronization

PLAN and DRIVE share server/SQLite state.

A completed Planner action:

```text
optimistic UI change
    ↓
REST mutation
    ↓
SQLite transaction
    ↓
route revision increments
    ↓
SSE route.updated
    ↓
PLAN / DRIVE consumers refresh as needed
```

No `Apply Changes` button exists.

### 12.1 REST + SSE

REST performs mutations and normal reads. Server-Sent Events provide low-complexity local notifications.

```text
GET /api/events
```

Potential events:

- route.updated;
- favorite.updated;
- place.created/updated/deleted;
- navigation.updated.

WebSocket is intentionally not required for Planner v1.

### 12.2 Optimistic UI

Reordering/favorite/add/remove must feel immediate. The client updates local UI first, then sends the mutation.

If the server rejects it, the UI rolls back to the server state and displays a concise error.

### 12.3 Optimistic concurrency

Route mutations include:

```text
expected_revision
```

If client and server revisions differ, API returns `409 ROUTE_REVISION_CONFLICT`. Client fetches the authoritative route and reconciles rather than overwriting newer changes.

---

## 13. Revisions, Undo, and Redo

Routes use monotonic integer revisions. Every completed edit increments the number once.

`route_revisions` records high-level actions plus enough payload to undo/redo them.

Representative actions:

- add_item;
- remove_item;
- move_item;
- edit_item;
- reverse_block;
- reverse_route;
- optimize;
- rename_route.

Large actions such as Optimize contain a before/after representation as one event.

Undo/Redo is available through buttons and keyboard shortcuts:

- Ctrl+Z.
- Ctrl+Y.

Tooltips may state e.g. `Undo: Optimize route`.

---

## 14. Navigation Sessions and Progress

A Saved Route is a reusable plan. A Navigation Session is a specific drive.

```text
NavigationSession
  id
  route_id
  route_revision_started
  started_at
  finished_at
  current_item_id
```

```text
NavigationProgress
  session_id
  route_item_id
  status
  visited_at
```

Statuses:

```text
upcoming
active
visited
skipped
```

A new drive starts with fresh progress. Previous visited state never contaminates another session.

### 14.1 Automatic completion

A STOP is completed when approximately:

```text
distance < ~50 m
AND vehicle is map-matched to the relevant WVAN route leg
AND route progress reaches/passes the appropriate anchor area
```

This avoids false completion on nearby but topologically separate roads.

STOP completion shows a brief arrival/next-target message.

VIA completion is quiet and automatically advances.

### 14.2 Skip / Previous

`Skip stop` marks the current item skipped and activates the next applicable item.

`Previous stop` reactivates a previous visited/skipped item and builds a legal directed path back to it.

### 14.3 Live editing during a drive

Edits continue to produce route revisions. DRIVE consumes the new revision and preserves sensible already-completed progress.

Examples:

- adding a future stop adds upcoming progress;
- deleting the current stop activates the next valid item and reroutes;
- already visited items do not automatically return to upcoming.

DRIVE distinguishes route-plan changes from missed-turn rerouting in its user messages.

---

## 15. SQLite Data Model

User database: `data/navigator.db`.

Planner v1 uses these logical tables:

```text
user_places
favorites
routes
route_items
route_revisions
navigation_sessions
navigation_progress
app_state
```

`app_state` includes at minimum the single `active_route_id` and small Planner settings.

### 15.1 Transactions

Each route mutation that changes multiple records must be one SQLite transaction. Example reorder transaction:

```text
update item positions
+ insert route revision
+ increment route revision number
+ commit
```

Partial states are not permitted.

### 15.2 Migrations

User DB schema has a monotonic schema version. Migrations are explicit and testable.

Before any migration, the server creates a backup in `data/backups/`.

If migration fails:

- old DB remains recoverable;
- backup remains intact;
- Navigator reports the failure rather than destroying/reinitializing data.

---

## 16. Backend Module Boundaries

The existing server should not become a monolithic Planner file.

Target responsibilities:

```text
server.py                app bootstrap + existing telemetry/DRIVE endpoints
planner_api.py           Planner REST endpoints
places_service.py        catalog loading and place resolution
route_service.py         RouteItem operations / Optimize / Reverse / preview
planner_database.py      SQLite, transactions, migrations
planner_events.py        SSE notifications
```

Existing directed WVAN routing remains a separate subsystem and has no dependency on Planner DOM/UI concepts.

### 16.1 API surface

Representative REST surface:

```text
GET    /api/places
GET    /api/places/:id

GET    /api/routes
POST   /api/routes
GET    /api/routes/active
PUT    /api/routes/:id

POST   /api/routes/:id/items
PATCH  /api/routes/:id/items/:itemId
DELETE /api/routes/:id/items/:itemId

POST   /api/routes/:id/optimize
POST   /api/routes/:id/reverse
POST   /api/routes/:id/undo
POST   /api/routes/:id/redo

POST   /api/favorites/:placeId
DELETE /api/favorites/:placeId

POST   /api/user-places
PATCH  /api/user-places/:id
DELETE /api/user-places/:id

POST   /api/navigation/start
POST   /api/navigation/skip
POST   /api/navigation/previous
POST   /api/navigation/stop

GET    /api/events
```

Exact request/response schemas are defined in the implementation plan/tests, but must honor stable IDs, expected revisions, and fail-closed routing.

---

## 17. Planner Frontend Boundaries

Planner should not be implemented as another thousands-line extension of `static/app.js`.

Recommended modules:

```text
static/planner/index.html
static/planner/planner.js          bootstrap/state coordination
static/planner/planner.css
static/planner/api.js              REST + SSE client
static/planner/library.js          search/filter/list state
static/planner/map.js              marker/layer interactions
static/planner/route_editor.js     Route Item editor/reorder
static/planner/history.js          client undo/redo presentation
static/planner/search.js           normalized/fuzzy index
```

Reusable directed routing code remains in existing directed-nav modules or a shared extracted module, not duplicated in Planner.

---

## 18. Keyboard and Interaction Requirements

Minimum shortcuts:

```text
Ctrl+Z       Undo
Ctrl+Y       Redo
Ctrl+F       Focus Places search
Delete       Remove selected Route Item
Esc          Close details/filter/map modes
Up/Down      Navigate Library results when search/list focused
Enter        Select highlighted Place
Ctrl+Enter   Add highlighted Place to Route
```

Drag-and-drop must never be the only means to reorder: Up/Down buttons remain available.

### 18.1 Confirmation policy

Prefer Undo over confirmation dialogs for routine edits.

No confirmation for:

- remove Route Item;
- reorder;
- favorite toggle;
- skip;
- reversible block direction change.

Confirmation remains appropriate for larger non-local consequences such as:

- permanent Saved Route deletion;
- Clear large route;
- deleting a My Place referenced by Saved Routes.

---

## 19. Empty, Loading, and Error States

Planner must have explicit empty states rather than blank panels.

Examples:

- Empty Route: instruction to search, add via `+`, or double-click map.
- Empty Library result: `No places found`, with `Clear filters`.
- No Saved Routes: explain Draft autosave.

App shell should render immediately while catalogs/graph load in parallel. Avoid a full-page blocking spinner.

During route recalculation:

- state can show `Calculating route…`;
- previous geometry may remain dimmed;
- outdated revision results are ignored.

---

## 20. Performance Targets

Design targets on a normal desktop PC:

```text
Typing to visible search update   < 100–150 ms
Filter click visual update        immediate
Favorite toggle                   immediate
Route reorder visual update       immediate
Typical route preview target      < ~500 ms
Planner shell visible             < ~1 s
```

Library list uses virtualization so DOM size remains roughly proportional to visible results rather than total catalog size.

Marker clustering limits far-zoom map density.

---

## 21. Backup, Export, and Import

### 21.1 User-data backup

Planner menu includes:

- Export user data.
- Import user data.

Backup contains:

- My Places.
- Favorites.
- Saved Routes.
- references to Scenic/built-in stable IDs.
- relevant Planner settings.

Built-in catalog records are not copied wholesale.

Missing IDs during import generate warnings without discarding unrelated recoverable data.

### 21.2 Route format

Saved routes can be exported/imported separately using a versioned format (e.g. `.fh6route`) with an explicit `format_version`.

This format should be suitable as the later foundation for Cloud route sharing without requiring cloud implementation now.

---

## 22. Advanced Diagnostics

Planner settings include optional developer diagnostics:

- Show WVAN navigation anchors.
- Show directed road graph.

These are hidden/advanced by default and intended for support/debugging.

If a place routes incorrectly, the user can enable anchors/graph and provide a screenshot without needing binary inspection tooling.

---

## 23. Release-Time Catalog Validation

A release build must fail if built-in/curated catalog validation finds structural errors such as:

- duplicate stable ID;
- missing name;
- unknown category;
- invalid coordinates;
- invalid/missing nav anchor;
- anchor point absent from compiled WVAN graph;
- duplicate source mapping;
- broken Scenic Road/Loop internal path;
- invalid declared reversibility.

For Scenic blocks validate:

- entry and exit anchors exist;
- every internal directed segment exists;
- configured direction is legal;
- reverse path exists when `reversible=true`.

---

## 24. Testing Strategy

### 24.1 Unit tests

- Search/fuzzy scoring.
- Filters and chips.
- Route Item operations.
- Locks.
- Reverse.
- Optimize.
- Revisions.
- Undo/Redo.
- SQLite migrations.
- Catalog parsing/validation.

### 24.2 API tests

- Create/open/rename route.
- Add/move/remove item.
- Revision conflict returns 409.
- Favorite mutation.
- User Place CRUD.
- Start/skip/previous navigation.
- SSE route update.
- DB transaction rollback on failure.

### 24.3 WVAN integration tests

Using the real compiled graph where available:

- one-way restrictions remain respected;
- no-right-turn restrictions remain respected;
- place anchor resolves;
- Scenic block fixed path validates;
- preview contains only legal directed legs.

### 24.4 UI architecture tests

Protect key invariants:

- Planner route preview uses Directed/WVAN authority.
- No active fallback to legacy LabsGG `shortestPath`.
- Library filters do not hide route geometry.
- Start Navigation disabled on unresolved route.
- map semantics match approved click/double-click/right-click/Shift+click behavior.

### 24.5 Browser-flow tests

Core flows:

```text
Search → Add → Add → reorder → Start Navigation
Double click map → Waypoint → Undo
Optimize → Undo
Planner edit while DRIVE active
Reload Planner → Draft preserved
Restart server → SQLite route preserved
```

---

## 25. Release Gate

Every Planner release must freshly pass:

```text
Python tests
JS tests
SQLite migration tests
catalog validation
WVAN graph validation
Scenic catalog validation
API smoke tests
clean release ZIP generation
unpack release ZIP
repeat required test matrix from unpacked ZIP
```

Raw game-owned `.nav/.owt/.oww/.owbs` assets must not be included in the release.

---

## 26. Explicit Non-Goals for Planner v1

The following are intentionally deferred:

- Cloud backend.
- Accounts.
- Cloud/Bridge architecture.
- Community routes/catalog uploads.
- Ratings/comments.
- Multilingual UI/content.
- Full mobile/touch Planner.
- Near Me.
- Search This Area.
- Distance-from-car sorting.
- Runtime internet POI scraping.
- Library multi-select.
- Scenic optimization profile.

Stable IDs, revisioned routes, versioned export formats, source separation, and modular APIs are chosen specifically so these future directions are not blocked.

---

## 27. Acceptance Definition for Planner v1

Planner v1 is ready when a user can:

1. Open PLAN from DRIVE in a separate/focused window.
2. Search/filter a pre-populated large Places Library quickly.
3. Favorite built-in/curated/user places.
4. Create/edit/delete My Places.
5. Add places and temporary map waypoints to the Active Route.
6. Add Scenic Roads/Loops as atomic mandatory blocks.
7. Reorder via drag or Up/Down.
8. Lock item position/direction.
9. Reverse and Optimize within declared constraints.
10. Undo/Redo completed edits.
11. Save/open/duplicate routes while Draft autosaves.
12. See valid directed WVAN preview and explicit unresolved legs.
13. Start Navigation only when the route is fully legal.
14. Continue editing PLAN while DRIVE live-updates to new revisions.
15. Automatically complete/skip/previous stops in a Navigation Session.
16. Restart the browser/server without losing user data.
17. Export/import user backup and individual routes.
18. Receive a release containing no raw game navigation assets.

The existing DRIVE behavior and Directed WVAN safety rules remain regression-protected throughout.
