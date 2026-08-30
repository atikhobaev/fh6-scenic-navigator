from __future__ import annotations
from dataclasses import replace
from .models import RawPlace, SourceRef
from .normalize import normalize_text


def _key(p: RawPlace):
    return (normalize_text(p.name), normalize_text(p.category))


def _merge(a: RawPlace, b: RawPlace) -> RawPlace:
    # Prefer a proven map/world position; otherwise preserve whichever record has one.
    pos = a if (a.map_x is not None and a.map_y is not None) or a.world_x is not None else b
    aliases = tuple(dict.fromkeys((*a.aliases, *b.aliases)))
    tags = tuple(dict.fromkeys((*a.tags, *b.tags)))
    provenance = tuple(dict.fromkeys((*a.provenance, *b.provenance)))
    sources = tuple({(s.provider, s.source_id, s.url, s.retrieved_at): s for s in (*a.sources, *b.sources)}.values())
    region = a.region or b.region
    return replace(
        pos,
        name=a.name,
        category=a.category,
        aliases=aliases,
        tags=tags,
        provenance=provenance,
        sources=sources,
        region=region,
    )


def dedupe_places(records: list[RawPlace] | tuple[RawPlace, ...], proximity_px: float = 12.0, proximity_m: float = 75.0) -> list[RawPlace]:
    out: list[RawPlace] = []
    by_source: dict[tuple[str, str], int] = {}
    for rec in records:
        skey = (rec.provider, rec.source_id)
        if skey in by_source:
            idx = by_source[skey]
            out[idx] = _merge(out[idx], rec)
            continue
        matched = None
        nk = _key(rec)
        for i, existing in enumerate(out):
            if _key(existing) != nk:
                continue
            # Distinct IDs from one authoritative provider are distinct game markers,
            # even when their visible title is generic (e.g. 200 "XP Board" rows).
            if rec.provider == existing.provider and rec.source_id != existing.source_id:
                continue
            if rec.world_x is not None and rec.world_z is not None and existing.world_x is not None and existing.world_z is not None:
                dx = float(rec.world_x) - float(existing.world_x)
                dz = float(rec.world_z) - float(existing.world_z)
                if (dx * dx + dz * dz) ** 0.5 > proximity_m:
                    continue
            elif rec.map_x is not None and rec.map_y is not None and existing.map_x is not None and existing.map_y is not None:
                dx = float(rec.map_x) - float(existing.map_x)
                dy = float(rec.map_y) - float(existing.map_y)
                if (dx * dx + dy * dy) ** 0.5 > proximity_px:
                    continue
            matched = i
            break
        if matched is None:
            by_source[skey] = len(out)
            out.append(rec)
        else:
            out[matched] = _merge(out[matched], rec)
            by_source[skey] = matched
    return out
