from __future__ import annotations
from datetime import date
from .dedupe import dedupe_places
from .models import RawPlace
from .normalize import lab_map_ref_to_world, stable_place_id, slug


def _runtime_place(p: RawPlace, snapper=None, place_id: str | None=None):
    if p.world_x is not None and p.world_z is not None:
        x, z = float(p.world_x), float(p.world_z)
        y = float(p.world_y or 0.0)
    elif p.map_x is not None and p.map_y is not None:
        x, z = lab_map_ref_to_world(p.map_x, p.map_y)
        y = 0.0
    else:
        return None
    snap = snapper.nearest(x, z) if snapper is not None else None
    if snap is not None and p.world_y is None:
        y = snap.y
    sources = [
        {k: v for k, v in {
            "provider": s.provider,
            "source_id": s.source_id,
            "url": s.url,
            "retrieved_at": s.retrieved_at,
        }.items() if v is not None}
        for s in p.sources
    ]
    quality = "probable" if len(sources) == 1 else "reviewed"
    default_visible = p.category not in {"xp_board", "mascot"}
    if snap is not None:
        if snap.distance_m > 500.0:
            quality = "unverified"
            default_visible = False
        elif len(sources) >= 2 and snap.route_validated and snap.distance_m <= 75.0:
            quality = "verified"
        elif len(sources) >= 2 and snap.distance_m <= 250.0:
            quality = "reviewed"
        elif snap.distance_m > 250.0:
            quality = "probable"
    return {
        "id": place_id or stable_place_id("game", p.category, p.name),
        "source": "game",
        "kind": "point",
        "name": p.name,
        "aliases": list(p.aliases),
        "category": p.category,
        "subcategory": "",
        "tags": list(dict.fromkeys((*p.tags, *( [p.region] if p.region else [] )))),
        "position": {"x": x, "y": y, "z": z},
        "navigation": {
            "anchor_point_id": snap.point_id if snap else None,
            "snap_distance_m": snap.distance_m if snap else None,
            "route_validated": snap.route_validated if snap else False,
        },
        "surface": "unknown",
        "access": "normal",
        "scenic_score": 0,
        "default_visible": default_visible,
        "featured": False,
        "quality": quality,
        "sources": sources,
    }


def build_runtime_catalog(records, catalog_version: str | None = None, snapper=None):
    merged = dedupe_places(list(records))
    places = []
    excluded = 0
    base_ids = [stable_place_id("game", p.category, p.name) for p in merged]
    base_counts = {base: base_ids.count(base) for base in set(base_ids)}
    used_ids = set()
    for p, base in zip(merged, base_ids):
        place_id = base
        if base_counts[base] > 1:
            place_id = f"{base}.{slug(p.provider)}_{slug(p.source_id)}"
        # Defensive collision guard for malformed provider snapshots.
        if place_id in used_ids:
            n = 2
            candidate = f"{place_id}_{n}"
            while candidate in used_ids:
                n += 1; candidate = f"{place_id}_{n}"
            place_id = candidate
        row = _runtime_place(p, snapper=snapper, place_id=place_id)
        if row is None:
            excluded += 1
        else:
            used_ids.add(place_id)
            places.append(row)
    places.sort(key=lambda p: p["id"])
    return {
        "schema_version": 1,
        "catalog_version": catalog_version or date.today().isoformat(),
        "places": places,
        "build": {
            "input_records": len(records),
            "deduplicated_records": len(merged),
            "excluded_unpositioned": excluded,
            "runtime_places": len(places),
            "snapped_places": sum(1 for p in places if p["navigation"]["anchor_point_id"] is not None),
        },
    }
