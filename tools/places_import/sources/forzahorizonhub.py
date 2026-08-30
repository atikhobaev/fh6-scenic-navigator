"""Complete bundled 796-marker FH6 inventory used by the private Navigator build."""
from __future__ import annotations

import json
from pathlib import Path

from ..models import RawPlace, SourceRef
from ..normalize import lab_map_ref_to_world

_SNAPSHOT = Path(__file__).resolve().parents[1] / "snapshots" / "full_796_inventory.json"
_LABS_URL = "https://forza.labsgg.com/interactive-map"
_DAMNMODZ_BARN = "https://damnmodz.com/wiki/forza-horizon-6/map/barn-finds/"
_DAMNMODZ_TREASURE = "https://damnmodz.com/wiki/forza-horizon-6/map/treasure-cars/"


def load_snapshot() -> list[RawPlace]:
    doc = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))
    retrieved = str(doc.get("retrieved_at") or "") or None
    out: list[RawPlace] = []
    for row in doc.get("records") or []:
        map_x, map_y = float(row["map_x"]), float(row["map_y"])
        world_x, world_z = lab_map_ref_to_world(map_x, map_y)
        coordinate_quality = str(row.get("coordinate_quality") or "")
        category = str(row["category"])
        if coordinate_quality == "source_exact":
            provider = "damnmodz"
            url = _DAMNMODZ_BARN if category == "barn_find" else _DAMNMODZ_TREASURE
        else:
            provider = "forzalabs_proxy"
            url = _LABS_URL
        tags = list(row.get("tags") or [])
        if coordinate_quality:
            tags.append(coordinate_quality)
        out.append(RawPlace(
            provider=provider,
            source_id=str(row["source_id"]),
            name=str(row["name"]),
            category=category,
            map_x=map_x,
            map_y=map_y,
            world_x=world_x,
            world_z=world_z,
            aliases=tuple(row.get("aliases") or ()),
            tags=tuple(tags),
            region=row.get("region"),
            provenance=(url,),
            sources=(SourceRef(provider, str(row["source_id"]), url, retrieved),),
        ))
    return out
