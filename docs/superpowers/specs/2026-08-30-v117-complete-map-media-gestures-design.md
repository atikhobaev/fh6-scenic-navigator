# FH6 Scenic Navigator v1.17 — Complete Map, Offline Media, and Gesture Arbitration

**Date:** 2026-08-30
**Status:** Approved in chat; written specification for review
**Base:** FH6 Scenic Navigator v1.16.3

## 1. Goal

Turn Planner into a complete exploration map without sacrificing route planning usability:

1. Panning the map must work even when the pointer starts on a POI marker.
2. Clicking a marker must still open/select it when the pointer does not actually drag.
3. The bundled catalog should contain every marker that the configured external-map adapters can prove with an exact source position, rather than the current small curated subset.
4. Places with available source screenshots should display those images in the on-map popover while the runtime remains fully offline.
5. External records must remain factual and attributable; no guessed positions or fabricated photos enter the runtime catalog.

## 2. User-visible behavior

### 2.1 Marker vs map gesture

A pointer-down on any ordinary POI marker, selected POI marker, cluster, or route marker initially enters a pending gesture state.

- movement below **5 CSS pixels**: release counts as a click and normal marker action runs;
- movement of **5 CSS pixels or more**: the gesture becomes map pan, marker click is cancelled, and the map tracks the pointer until release;
- text/SVG/image dragging and browser selection are disabled inside the map surface;
- route markers remain clickable but do not form a mouse-drag dead zone;
- touch follows the same threshold semantics where Pointer Events are available.

The map must never require the user to find empty pixels before panning.

## 3. Canonical multi-source catalog

The runtime continues to expose one normalized `Place` model. Source-specific records are build inputs, never separate runtime layers unless their categories differ semantically.

### 3.1 Sources

Adapters are defined for:

1. **Guides4Gamers** — primary broad official/game POI corpus: races, PR stunts, collectibles, landmarks, houses, events, stories, boards, mascots and similar categories.
2. **MapMaster** — secondary broad corpus used to add records missing from the primary source and to cross-check names/categories/positions.
3. **ForzaLabs** — official-map-like taxonomy/reference data and any extractable POI records exposed by the map source; existing road/nav datasets remain separate from POI ingestion.
4. **ForzaHorizon.app** — community locations such as scenic spots, secret roads, jumps, easter eggs, collectibles and Other, with player screenshots when publicly available.

The importer architecture must allow additional adapters without changing `PlacesService` or Planner UI.

### 3.2 Definition of “all points”

For this release, “all points” means **all public records returned by an adapter that include a stable source identity and an exact source-map position that can be deterministically converted into FH6 map/world coordinates**.

A record that lacks a proven position is retained in build evidence but is not emitted into `builtin_places.json`, `community_places.json`, or another runtime catalog.

No coordinate may be inferred from:

- a place name;
- a screenshot;
- a prose region description;
- proximity to another named POI;
- visual guessing on the map.

## 4. Source snapshot boundary

Runtime never scrapes external services. Build-time source snapshots are stored under `tools/place_import/snapshots/` in a compact factual form required to reproduce the catalog.

Each raw snapshot item may retain:

```text
provider
source_id
source_url
name
category/subcategory
source_position
image_url (build-time only)
author/contributor
published/approved state
source metadata needed for attribution/dedupe
```

Third-party prose descriptions are not copied wholesale. Only factual fields required for discovery/navigation plus minimal attribution are retained.

## 5. Coordinate adapters

Each provider owns a coordinate adapter with an explicit transform contract:

```python
SourcePoint -> MapPoint | WorldPoint
```

Every transform must have fixture tests using known source records and known Navigator positions.

After conversion:

1. keep the real source position for marker display;
2. snap a separate navigation anchor to Directed WVAN;
3. store `nav_anchor_point_id` and `nav_snap_distance`;
4. reject records outside known FH6 map bounds;
5. flag excessive WVAN snap distance instead of moving the visible marker.

## 6. Deduplication

The merger receives normalized source records and emits canonical places.

Order of evidence:

1. explicit cross-provider ID mapping when known;
2. normalized exact/alias name match plus compatible category;
3. spatial proximity within a category-sensitive threshold;
4. normalized name similarity + spatial proximity.

A merge never discards provenance. Canonical records contain all contributing providers in `source_metadata.providers[]`.

Records that share a location but represent genuinely different gameplay objects remain separate (for example a landmark and a speed trap at the same coordinates).

## 7. Catalog taxonomy

The layer registry remains the single UI taxonomy. Import adapters map provider categories into existing layers and may add missing leaf categories without changing group semantics.

Target broad coverage includes at minimum:

- settlements/landmarks/scenic/photo;
- houses/festival/story/job/event locations;
- road/dirt/cross-country/street/touge/drag/time-attack races;
- speed traps/speed zones/danger signs/drift zones/trailblazers;
- barn finds/treasure cars/aftermarket cars;
- XP/bonus boards and regional mascots;
- photo subjects and treasure chests where currently public;
- community scenic spots/secret roads/jumps/easter eggs/collectibles/other.

All high-density categories remain disabled by the Recommended preset but are discoverable via filters/search.

## 8. Offline media pipeline

### 8.1 Build-time only downloads

If a normalized source record exposes a public screenshot/image URL and policy allows it for this private build, the build pipeline downloads it once and stores a local derivative.

Runtime fields are local only:

```text
image: /media/places/<provider>/<stable-name>.webp
image_thumb: /media/places/<provider>/<stable-name>.thumb.webp
```

The remote image URL is retained only in provenance/build evidence.

### 8.2 Processing

- decode source image;
- normalize EXIF orientation;
- generate bounded WebP full image;
- generate smaller WebP thumbnail;
- compute SHA-256;
- deterministic filename from provider + source ID/hash;
- do not fail the whole catalog when one image is unavailable;
- validator rejects runtime HTTP(S) image references and missing local files.

### 8.3 Popover

When `image_thumb`/`image` exists, the popover renders the image above metadata using a fixed aspect-ratio container and lazy decoding. Clicking/dragging the image itself must not interfere with the map gesture model.

When no image exists, the popover remains compact with no blank image placeholder.

## 9. Build artifacts

Runtime catalogs remain split by ownership:

```text
static/data/builtin_places.json
static/data/scenic_catalog.json
static/data/community_places.json
```

Build reports are added:

```text
tools/place_import/out/import_report.json
tools/place_import/out/unresolved_records.json
```

`import_report.json` records per-provider totals, normalized count, emitted count, duplicate merges, rejected/out-of-bounds/unresolved counts, image download/cache totals, and final runtime counts by layer.

## 10. Performance

The Planner must remain responsive with ~1,000+ POIs loaded.

- filtering/search stays client-side;
- existing marker clustering remains enabled for normal POIs;
- selected/route markers never cluster;
- marker DOM is rendered only for visible/clustering outputs, not one permanent DOM element per record when zoomed out;
- images are lazy-loaded and thumbnails are used in search/popover where sufficient.

Target interactions on normal desktop hardware:

- layer toggle under 100 ms perceived;
- search update under 150 ms;
- map pan remains smooth with dense layers enabled.

## 11. Error handling

- provider snapshot unavailable: retain previous verified snapshot, mark build report stale; do not silently emit an empty catalog;
- coordinate transform unresolved: evidence only, no runtime marker;
- image unavailable/corrupt: text-only place remains valid;
- duplicate ambiguous: keep both and flag for review rather than destructive merge;
- WVAN anchor unavailable: marker may remain discoverable only if catalog policy allows non-routable records, with destination action disabled and explicit reason;
- runtime never calls external map/image providers.

## 12. Testing

### Gesture tests

- pointer down/up on marker under threshold selects marker;
- pointer down on marker + >5 px movement pans map and does not select marker;
- ordinary map drag still works;
- selected and route markers do not block pan;
- marker SVG/text cannot be browser-selected/dragged.

### Import tests

Per-provider offline fixtures verify:

- source parsing;
- stable ID/category mapping;
- coordinate transform;
- out-of-bounds rejection;
- dedupe and provenance merge;
- WVAN snapping;
- source-specific failures remain fail-closed.

### Media tests

- deterministic local filenames;
- successful image conversion produces local WebP + thumbnail + checksum;
- failed download leaves place valid without runtime remote URL;
- catalog validator rejects remote runtime images and missing local files;
- popover shows image only when local asset exists.

### Release gates

- complete Python suite;
- complete JS suite;
- catalog validator;
- import report sanity checks;
- real Directed-WVAN preview regression;
- clean unpacked ZIP smoke;
- no raw game `.nav/.owt/.oww/.owbs` assets bundled;
- no runtime dependency on external map services other than existing map-tile behavior.

## 13. Release acceptance criteria

v1.17 is accepted when:

1. The user can begin dragging the map directly on top of any POI marker and the map pans after the gesture threshold.
2. A simple click still opens the correct marker popover.
3. Dense marker layers do not create drag dead-zones or selectable SVG/text artifacts.
4. The release catalog is generated by the multi-source adapter pipeline and its report states exactly how many public source records were imported/rejected/merged.
5. All source records with proven exact positions that are supported by configured adapters are visible in the appropriate filter layer.
6. Community/source screenshots that were successfully cached are visible in popovers fully offline.
7. Places without photos have a compact text-only popover.
8. Navigation continues to target legal Directed-WVAN anchors rather than raw off-road marker coordinates.
9. Runtime catalogs contain no external image URLs and no guessed coordinates.
