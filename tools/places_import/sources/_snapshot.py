from __future__ import annotations
import json
from pathlib import Path
from ..models import RawPlace, SourceRef


def load_rows(filename: str) -> list[RawPlace]:
    path = Path(__file__).resolve().parents[1] / "snapshots" / filename
    doc = json.loads(path.read_text(encoding="utf-8"))
    provider = str(doc["provider"])
    retrieved = str(doc.get("retrieved_at") or "") or None
    urls = doc.get("sources", {})
    out: list[RawPlace] = []
    for row in doc.get("records", []):
        category = str(row["category"])
        url = urls.get(category)
        out.append(RawPlace(
            provider=provider,
            source_id=str(row["source_id"]),
            name=str(row["name"]),
            category=category,
            map_x=row.get("map_x"),
            map_y=row.get("map_y"),
            aliases=tuple(row.get("aliases", ())),
            tags=tuple(row.get("tags", ())),
            region=row.get("region"),
            provenance=(url,) if url else (),
            sources=(SourceRef(provider, str(row["source_id"]), url, retrieved),),
        ))
    return out
