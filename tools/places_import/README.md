# FH6 Places Importer — v1.17.2

Planner runtime and the normal Windows launcher are **offline for catalog/road data**. They never fetch third-party POI, screenshot, or road datasets during startup.

## Bundled data boundary

The release contains:

- `static/data/builtin_places.json` — built-in game POIs generated from reviewed local snapshots;
- `static/data/scenic_catalog.json` — curated Navigator destinations;
- `static/data/fh6_roads.json` — bundled LabsGG-derived road/route-node dataset used by the legacy map road overlay;
- `static/data/fh6_navgraph_v1.json.gz` — bundled authoritative Directed WVAN routing graph;
- `tools/places_import/snapshots/` — reproducible factual source snapshots used by the offline catalog builder.

Current bundled snapshot contains **796 game POIs across 38 source categories**. Of these, 24 hidden-car records retain source-exact published coordinates. The remaining 772 records use deterministic positions sampled from the bundled ForzaLabs road geometry so the complete public inventory is immediately visible and routable in this private pet-project build. `source_inventory.json` records that coordinate-quality split explicitly.

## User rebuild

Run:

```bat
update_map_data.bat
```

or:

```bash
python -u -m tools.places_import.offline_rebuild
```

The rebuild has five visible stages, validates the result, and publishes JSON files atomically. **Internet is not used.**

## Developer-only network importer

`tools.places_import.bootstrap` is retained only as a developer/source-research utility and is not called by `launcher.py` or `update_map_data.bat`. A release must not depend on it for normal operation.

## Coordinate policy

Each runtime point is snapped separately to the bundled Directed-WVAN graph. Source-exact records keep their published marker position. Inventory records whose exact source coordinate was not retained use a deterministic bundled-road proxy position and are tagged `road_network_proxy`; the WVAN anchor under `navigation` is used for legal routing. No runtime network lookup is required.

## Offline media policy

Runtime catalogs may reference only local `/media/places/...` paths. External HTTP(S) image references fail catalog validation. The normal launcher never downloads screenshots.
