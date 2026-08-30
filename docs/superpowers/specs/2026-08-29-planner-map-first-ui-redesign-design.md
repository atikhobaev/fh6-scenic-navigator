# FH6 Scenic Navigator — Map-First Planner UI Redesign Design

**Date:** 2026-08-29

**Status:** Approved in chat; written design awaiting final user review before implementation planning.

**Base:** FH6 Scenic Navigator v1.15 Route Planner.

## 1. Goal

Redesign `/planner/` into a map-first route-planning experience that feels like a polished interactive game map rather than a three-panel administration tool, while preserving every useful marker category and all existing directed-WVAN routing capabilities.

The redesign has five primary goals:

1. Make the map the visual center of the Planner.
2. Make filtering hundreds of POIs fast and understandable using a layer/legend model inspired by ForzaLabsGG.
3. Keep every marker category available, but show a calm useful default set on first launch.
4. Replace separate place-detail views with an on-map popover containing image, metadata, and route actions.
5. Make the existing standard Grand Tour route visible and usable from Planner as a built-in route.

## 2. Reference principles

### 2.1 ForzaLabsGG interaction principles

Use as UX inspiration, not as copied implementation/assets:

- searchable marker catalog;
- grouped layer categories;
- enable-all / disable-all style bulk controls;
- per-category visibility toggles;
- clear icon differentiation between marker types;
- map legend as a first-class navigation tool;
- road/surface-related filters kept close to map controls.

The current ForzaLabsGG FH6 map exposes categories including Discovery, Story, PR Stunts, In World Events and Races, with marker types such as Barn Find, Treasure Car, Photography, House, Horizon Festival, Speed Trap, Speed Zone, Danger Sign, Drift Zone, Trailblazer, Car Meet, Street Race, Road Race, Touge Race, Rally Race and Cross Country Race.

### 2.2 ForzaHorizon.app content principles

Use as a source of community location facts and local offline screenshots for this private pet project.

The source currently contains community-approved categories such as:

- Barn Find;
- Easter Egg;
- Scenic Spot;
- Jump;
- Secret Road;
- Collectible;
- Other.

Community pins can contain a player-submitted in-game screenshot and exact map placement. The importer should preserve source attribution metadata even though screenshots are cached into the local project.

## 3. Overall Planner layout

Replace the existing visually equal three-panel layout with a map-first shell.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ FH6 NAV  DRIVE | PLAN   Search…              Route: Grand Tour Japan   ⋯    │
├───────────────┬────────────────────────────────────────────────┬─────────────┤
│ MAP FILTERS   │                                                │ ROUTE       │
│               │                                                │             │
│ Quick chips   │                                                │ Stops       │
│ Layers        │                    MAP                         │             │
│ Surface       │                                                │ Optimize    │
│ Sources       │                                                │ Reverse     │
│               │                                                │             │
│               │                                                │ START       │
└───────────────┴────────────────────────────────────────────────┴─────────────┘
```

### 3.1 Map

The map owns the majority of width and is never replaced by a detail page.

### 3.2 Left filter rail

Default width: approximately 280–320 px.

May be resized and collapsed.

Contains search, quick chips, grouped visibility layers, surface/source filters, category counts and bulk visibility actions.

It does **not** contain a permanently scrolling card catalog by default.

### 3.3 Right route rail

Default width: approximately 320–380 px.

Keeps the existing route-builder responsibilities:

- active route;
- drag reorder;
- up/down controls;
- STOP/VIA/Scenic blocks;
- Optimize;
- Reverse;
- Start Navigation;
- warnings;
- total distance/time.

Can be collapsed to maximize map space.

## 4. Search UX

Global Planner search lives in the top bar.

```text
Search places, roads, events…
```

Search covers the entire catalog, not only currently visible layers.

Search fields include:

- canonical name;
- aliases;
- category;
- subcategory;
- tags;
- region;
- source-specific label;
- route/collection name where appropriate.

### 4.1 Search behavior

- fuzzy matching remains enabled;
- results update immediately with a short debounce;
- a floating result panel appears over the map below the search field;
- results show icon, name, category and optional thumbnail;
- selecting a hidden-by-filter result temporarily reveals that marker and centers the map;
- closing search restores ordinary filter visibility rules;
- search never navigates to a separate details screen.

## 5. Quick filters

Always-visible quick chips:

```text
★ Favorites   🏔 Scenic   📷 With Photos   📍 In Route
```

These combine with layer filters rather than replacing them.

## 6. Full layer taxonomy

All useful POIs remain available. Nothing is removed merely because the map can become dense.

### 6.1 Discover

- Settlements / Cities / Villages
- Landmarks
- Scenic Spots
- Scenic Roads
- Photo Spots / Photography
- Houses
- Festival Sites
- Easter Eggs
- Other Discovery

### 6.2 Gameplay / Story

- Horizon Festival / Story locations
- Day Trip / story activities
- Yuji's Auto
- Moto Auto Zine
- Drift Club Japan
- Raku Raku Job
- Wrist Band / showcase events
- other supported story activities

### 6.3 PR Stunts

- Speed Traps
- Speed Zones
- Danger Signs
- Drift Zones
- Trailblazers

### 6.4 Events

- Car Meets
- Drag Meetups
- Time Attack Tracks
- other world events

### 6.5 Races

- Street Race
- Road Race
- Touge Race
- Drag Race
- Rally Race
- Cross Country Race

### 6.6 Collect / Cars

- Barn Finds
- Treasure Cars
- Used Car locations
- Bonus / XP Boards
- Collectibles
- Mascot / character markers
- other collectible or car-related POIs

### 6.7 Community

- Scenic Spots
- Secret Roads
- Jumps
- Easter Eggs
- Community Collectibles
- Community Other

### 6.8 My

- My Places

## 7. Default visibility

All categories exist in the filter UI from the start, but the map should open with a calm recommended preset.

### 7.1 Enabled by default

- Settlements;
- Landmarks;
- Scenic Spots;
- Scenic Roads;
- Photo Spots;
- My Places;
- Active Route markers regardless of filters.

### 7.2 Disabled by default

High-density or task-specific categories, including:

- Barn Finds;
- Treasure Cars;
- Boards;
- generic Collectibles;
- races;
- PR Stunts;
- story activities;
- most events;
- community Other.

The user can enable any of them with one click.

### 7.3 Persistence

After the user changes layer visibility, save the state in Planner settings and restore it on future launches.

Provide:

- `Enable all`;
- `Disable all`;
- `Recommended` reset.

`Recommended` restores the default preset above.

## 8. Filter rail interaction

Groups are collapsible.

Example:

```text
DISCOVER                         58 visible
▾
  ☑ Settlements                 18
  ☑ Landmarks                   21
  ☑ Scenic Spots                10
  ☑ Scenic Roads                 8
  ☑ Photo Spots                 14
  ☐ Houses                       8

PR STUNTS                        0 visible
›

RACES                            0 visible
›
```

Each row contains:

- category icon;
- checkbox/toggle;
- human-readable category name;
- result count after current search/source/surface filters.

Clicking the group checkbox toggles the whole group.

## 9. Marker visual system

Create an original marker/icon system inspired by the clarity of interactive-map legends but not dependent on external runtime assets.

### 9.1 Marker requirements

Each marker has:

- category-specific pictogram;
- compact base footprint;
- consistent stroke/border treatment;
- selected state;
- hover state;
- favorite indicator when applicable;
- route-state override when a POI is part of the active route.

### 9.2 Marker hierarchy

Priority:

1. Active route stop / active navigation target
2. Selected marker
3. Favorites
4. Scenic / featured places
5. Normal enabled POIs
6. Dense collectible/event layers

### 9.3 Route markers

Route stops use numbered markers and never disappear due to filters or clustering.

### 9.4 Clustering

Normal POI layers cluster at low zoom.

Clusters:

- show count;
- expand on click/zoom;
- never absorb active route markers;
- never absorb selected markers;
- keep Scenic Road geometry separate.

## 10. Place popover

Clicking a marker opens an anchored popover on the map.

No separate details page is opened.

No Library-to-Details navigation state exists in the redesigned Planner.

### 10.1 Photo place

```text
┌──────────────────────────────────┐
│          LOCAL IMAGE             │
│                                  │
├──────────────────────────────────┤
│ Hidden Viewpoint              ☆  │
│ Scenic Spot · Community          │
│                                  │
│ [ + ADD TO ROUTE ]               │
│ [ SET DESTINATION ]              │
│ [ FAVORITE ]                     │
└──────────────────────────────────┘
```

### 10.2 Place without image

The popover becomes shorter. Do not render a large blank image box.

### 10.3 Popover actions

For ordinary places:

- Add to route;
- Set destination;
- Favorite / unfavorite;
- Save to My Places where applicable;
- Edit/Delete for My Places only.

For temporary map positions, continue supporting waypoint/via creation via context menu.

### 10.4 Scenic Road popover

Shows:

- image if available;
- road name;
- distance;
- surface;
- recommended direction;
- `Add to route`;
- direction toggle if reversible;
- map highlight of its geometry.

## 11. Offline images

The Planner must remain usable without internet access.

### 11.1 Asset storage

Community screenshots acquired for this private project are cached inside the project, preferably as WebP thumbnails plus optional higher-resolution variants.

Suggested layout:

```text
static/media/places/
  community/
  builtin/
  curated/
```

### 11.2 Image metadata

Each imported image record keeps:

- local path;
- source provider;
- source spot ID;
- source page reference;
- contributor/author name when available;
- fetch timestamp;
- original image identifier/hash;
- local checksum.

### 11.3 Runtime rule

Planner UI uses local paths only.

No screenshot URL is required at runtime.

If an image is missing or corrupt, the place remains fully usable and the popover falls back to text-only layout.

## 12. Community content ingestion

Extend the existing build-time importer with a ForzaHorizon.app adapter.

Importer should collect, when available:

- stable external spot ID;
- title;
- category;
- exact source map position;
- screenshot;
- contributor;
- likes/popularity if useful for ranking;
- source URL/reference;
- approval/publication metadata where available.

The adapter then runs through the existing pipeline:

```text
source
→ normalize
→ coordinate transform
→ dedupe
→ WVAN snap
→ confidence/quality
→ local image processing
→ runtime catalog
```

Do not invent map coordinates. A record without a proven coordinate transform may be retained as importer evidence but is not released as a routed runtime place.

## 13. Built-in Grand Tour route

The existing standard/base Grand Tour becomes visible in Planner.

### 13.1 Route selector

Add a `Built-in Routes` group to the route selector:

```text
ROUTES
Built-in
  Grand Tour Japan

Saved
  Mountain Drive
  Night Route

Draft
  Draft Route
```

### 13.2 Behavior

Selecting `Grand Tour Japan`:

- renders the entire built-in route on the map;
- displays its route items in the right rail;
- allows `START NAVIGATION` directly;
- keeps the built-in definition immutable.

### 13.3 Edit-on-copy

If the user attempts a structural edit such as:

- add/remove stop;
- reorder;
- reverse;
- optimize;
- change Scenic direction;

Planner creates an editable user copy first.

Example name:

`Grand Tour Japan — Copy`

The built-in original remains unchanged.

Favorites or visual map state do not require copying the route.

## 14. Route/map integration

The active route remains visually dominant over enabled POI layers.

When a route is selected:

- route markers stay visible regardless of filters;
- route geometry stays visible regardless of filters;
- selecting a route item centers/highlights its marker or Scenic block;
- selecting a POI popover can append or set it as destination without closing Planner context.

## 15. Map context menu

Retain existing map actions:

- Set as destination;
- Add waypoint;
- Add via point;
- Save to My Places.

Double-click still adds a temporary waypoint.

Shift-click still supports quick route accumulation.

## 16. Responsive behavior

Desktop remains primary.

Wide mode:

`Filters | Map | Route`

Narrow mode:

- filter rail becomes a left drawer;
- route rail becomes a right drawer;
- map remains full-screen background;
- popovers remain map-anchored.

Do not build a separate mobile application in this redesign.

## 17. Performance targets

The redesigned UI must remain responsive with all catalog categories loaded.

Targets:

- search result update: under 150 ms on normal desktop hardware;
- filter toggle: immediate visual response;
- marker visibility update: under 100 ms for ordinary layer operations;
- route changes remain optimistic;
- clustering/virtual marker rendering prevents hundreds of DOM nodes from harming interaction;
- local thumbnails use bounded dimensions and lazy decode/loading.

## 18. Data-model changes

### 18.1 Place extensions

Add optional fields:

```text
image
image_thumb
image_attribution
image_source
external_source_id
popularity
```

Keep existing stable internal `place_id` as the primary identity.

### 18.2 Layer metadata

Maintain a central layer registry defining:

- layer ID;
- group;
- label;
- icon;
- default visibility;
- clustering behavior;
- marker priority;
- categories/subcategories mapped to the layer.

Do not hard-code layer behavior separately in several UI files.

### 18.3 Built-in route metadata

Built-in route definitions must have stable IDs and `read_only=true`.

A user copy receives a new UUID and ordinary saved-route semantics.

## 19. Backend/API changes

Prefer extending existing APIs rather than creating a separate map backend.

Required capabilities:

- `/api/places` returns image/layer metadata;
- route listing exposes built-in and user routes distinctly;
- opening a built-in route does not write it into SQLite;
- edit-on-copy endpoint/service operation creates a normal user route from a built-in definition;
- diagnostics can report missing local image files;
- catalog validation checks local image references.

## 20. UI module boundaries

Keep modules focused.

Suggested responsibilities:

- `planner_layers.js` — layer registry/filter state;
- `planner_markers.js` — marker/icon rendering and clustering;
- `planner_popover.js` — anchored place/scenic popovers;
- `planner_search.js` — floating global search UI;
- existing route editor module — route rail only;
- existing API module — REST/SSE communication;
- importer adapter — source ingestion, not runtime UI.

Avoid putting all map redesign logic into `planner.js`.

## 21. Error handling

### Missing photo

Text-only popover, no broken-image icon.

### Invalid imported coordinates

Exclude from routed runtime catalog; record importer validation warning.

### Broken image metadata

Catalog validator warns/fails release according to severity.

### Built-in route cannot resolve on current graph

Show `Built-in route unavailable` and disable Start Navigation. Never fall back to a fabricated path.

### Search result hidden by layer

Temporarily reveal selected search result without permanently changing the layer toggle.

## 22. Testing

### 22.1 Layer/filter tests

Verify:

- all supported categories exist in registry;
- default preset enables only Settlements/Landmarks/Scenic/Photo/My Places;
- Enable all / Disable all / Recommended work;
- filter state persists;
- active route markers remain visible.

### 22.2 Marker/popover tests

Verify:

- marker type maps to correct layer/icon definition;
- selected marker is not clustered;
- route marker is not clustered;
- click opens popover rather than detail page;
- photo popover uses local asset;
- missing photo produces compact text-only popover;
- actions call existing route/favorite APIs.

### 22.3 Built-in route tests

Verify:

- Grand Tour Japan appears under Built-in Routes;
- selecting it renders route items/geometry;
- Start Navigation works without copying;
- first structural edit creates user copy;
- original built-in route remains unchanged.

### 22.4 Importer tests

Use offline fixtures to verify:

- community spot parsing;
- screenshot acquisition metadata;
- deterministic local filenames;
- coordinate transform;
- WVAN snapping;
- dedupe;
- missing coordinate rejection;
- image checksum/reproducibility where practical.

Network access is not required for ordinary unit tests.

### 22.5 Regression gates

Continue existing gates:

- Python suite;
- JS suite;
- catalog validator;
- real WVAN graph validation;
- HTTP/SSE smoke;
- clean unpacked ZIP tests;
- raw game asset hygiene.

## 23. Release behavior

Target next build: `v1.16 MAP-FIRST PLANNER` rather than a tiny patch number because the UI experience changes materially.

Release must contain:

- full offline runtime code;
- bundled verified catalogs;
- bundled cached screenshots selected by importer;
- Built-in Grand Tour route;
- no runtime dependency on ForzaLabsGG or ForzaHorizon.app;
- provenance metadata for imported content.

## 24. Explicitly out of scope

This redesign does not add:

- Cloud accounts;
- public route sharing;
- multi-user editing;
- full mobile-specific planner;
- runtime scraping of external map services;
- automatic background internet updates;
- new authoritative routing algorithms.

Directed WVAN remains the authoritative router.

## 25. Acceptance criteria

The redesign is complete when a user can:

1. Open Planner and immediately see a clean map with Settlements, Landmarks and Scenic/Photo locations.
2. Open the filter rail and discover every other marker category, including Barn Finds, Treasure Cars, races, PR Stunts, boards and collectibles.
3. Enable dense layers without losing route visibility or map usability.
4. Search the full catalog even when matching layers are hidden.
5. Click a marker and act entirely from an on-map popover without leaving the map.
6. See local screenshots in popovers while completely offline.
7. Select `Grand Tour Japan` under Built-in Routes and see the complete base route in Planner.
8. Start the built-in route directly.
9. Edit the built-in route and transparently receive an editable user copy.
10. Build or modify a route while all routing continues to use legal Directed WVAN paths.
