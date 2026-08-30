from __future__ import annotations

import argparse
import json
from pathlib import Path

from .build import load_navgraph
from .snap import NavGraphSnapper
from route_preview import DirectedGraph


def _json_bytes(doc: dict) -> bytes:
    return (json.dumps(doc, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")



def _route_via(graph: DirectedGraph, anchors: list[int]) -> tuple[list[int], float]:
    if len(anchors) < 2:
        raise ValueError("scenic loop requires at least two anchors")
    points = [int(anchors[0])]
    total = 0.0
    for start, goal in zip(anchors, anchors[1:]):
        leg = graph.route_between(int(start), int(goal), objective="fastest")
        if leg is None:
            raise ValueError(f"no legal directed path for curated loop: {start}->{goal}")
        leg_points = [int(x) for x in leg["point_ids"]]
        points.extend(leg_points[1:])
        total += float(leg["distance_m"])
    return points, round(total, 3)


def _seed_grand_tour(out: dict, graph_payload: dict) -> None:
    places = list(out.get("places") or [])
    anchors = [int(p["navigation"]["anchor_point_id"]) for p in places if (p.get("navigation") or {}).get("anchor_point_id") is not None]
    if len(anchors) != len(places) or len(anchors) < 2:
        return
    graph = DirectedGraph.from_payload(graph_payload)
    clockwise_stops = [*anchors, anchors[0]]
    counter_stops = [anchors[0], *reversed(anchors[1:]), anchors[0]]
    clockwise, clockwise_distance = _route_via(graph, clockwise_stops)
    counter, counter_distance = _route_via(graph, counter_stops)
    block = {
        "id": "curated.loop.grand_tour_japan",
        "type": "loop",
        "name": "Grand Tour Japan",
        "tags": ["scenic", "grand_tour", "all_regions"],
        "surface": "mixed",
        "scenic_score": 5,
        "reversible": True,
        "recommended_direction": "clockwise",
        "clockwise_anchor_point_ids": clockwise,
        "counterclockwise_anchor_point_ids": counter,
        "clockwise_distance_m": clockwise_distance,
        "counterclockwise_distance_m": counter_distance,
        "quality": "verified",
    }
    blocks = [b for b in (out.get("blocks") or []) if b.get("id") != block["id"]]
    blocks.append(block)
    out["blocks"] = blocks
    collection = {
        "id": "curated.collection.grand_tour_destinations",
        "name": "Grand Tour Japan Destinations",
        "tags": ["scenic", "grand_tour"],
        "place_ids": [p["id"] for p in places],
    }
    collections = [c for c in (out.get("collections") or []) if c.get("id") != collection["id"]]
    collections.append(collection)
    out["collections"] = collections

def enrich_curated_catalog(*, input_path: Path, graph_path: Path, output_path: Path, catalog_version: str) -> dict:
    input_path = Path(input_path)
    doc = json.loads(input_path.read_text(encoding="utf-8"))
    if doc.get("schema_version") != 1:
        raise ValueError("unsupported curated schema_version")
    graph = load_navgraph(graph_path)
    snapper = NavGraphSnapper(graph)
    out = json.loads(json.dumps(doc))
    snapped = 0
    hidden = 0
    for place in out.get("places", []):
        pos = place.get("position") or {}
        hit = snapper.nearest(float(pos["x"]), float(pos["z"]))
        pos["y"] = hit.y
        place["position"] = pos
        nav = place.setdefault("navigation", {})
        nav.update({
            "anchor_point_id": hit.point_id,
            "snap_distance_m": hit.distance_m,
            "route_validated": hit.route_validated,
        })
        # Existing curated points are human-selected route destinations. WVAN snapping
        # validates the navigation anchor but does not invent a scenic rating.
        if hit.distance_m > 500.0:
            place["quality"] = "unverified"
            place["default_visible"] = False
            hidden += 1
        elif hit.route_validated and hit.distance_m <= 150.0:
            place["quality"] = "verified"
        else:
            place["quality"] = "reviewed"
        snapped += 1
    _seed_grand_tour(out, graph)
    out["catalog_version"] = catalog_version
    out["build"] = {
        "source": input_path.name,
        "snapped_places": snapped,
        "hidden_unverified": hidden,
        "navgraph_route_validated": bool((graph.get("capabilities") or {}).get("route_validated")),
    }
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(_json_bytes(out))
    return dict(out["build"])


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Snap the curated FH6 catalog to the bundled directed WVAN graph.")
    p.add_argument("--input", type=Path, default=Path("static/data/scenic_catalog.json"))
    p.add_argument("--graph", type=Path, default=Path("static/data/fh6_navgraph_v1.json.gz"))
    p.add_argument("--output", type=Path, default=Path("static/data/scenic_catalog.json"))
    p.add_argument("--catalog-version", default="2026.08.29.1")
    args = p.parse_args(argv)
    report = enrich_curated_catalog(input_path=args.input, graph_path=args.graph, output_path=args.output, catalog_version=args.catalog_version)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
