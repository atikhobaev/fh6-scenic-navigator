from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path

from .build_catalog import build_runtime_catalog
from .snap import NavGraphSnapper
from .sources.forzahorizonhub import load_snapshot as load_full_inventory

SNAPSHOT_DIR = Path(__file__).resolve().parent / "snapshots"


def load_navgraph(path: Path) -> dict:
    path = Path(path)
    raw = path.read_bytes()
    if path.suffix == ".gz":
        raw = gzip.decompress(raw)
    doc = json.loads(raw.decode("utf-8"))
    if doc.get("format") != "fh6-navgraph-v1":
        raise ValueError("invalid navgraph format")
    return doc


def load_source_inventory() -> dict:
    return json.loads((SNAPSHOT_DIR / "source_inventory.json").read_text(encoding="utf-8"))


def _json_bytes(doc: dict) -> bytes:
    return (json.dumps(doc, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def build_official_catalog(*, graph_path: Path, output_path: Path, catalog_version: str) -> dict:
    graph = load_navgraph(graph_path)
    snapper = NavGraphSnapper(graph)
    records = load_full_inventory()
    doc = build_runtime_catalog(records, catalog_version=catalog_version, snapper=snapper)
    inventory = load_source_inventory()
    doc["build"].update({
        "reported_source_markers": int(inventory["reported_marker_upper_bound"]),
        "coordinate_records_captured": int(inventory["coordinate_records_captured"]),
        "coordinate_quality": dict(inventory.get("coordinate_quality") or {}),
        "coverage_limited_reason": str(inventory["coverage_limited_reason"]),
        "source_inventory_date": inventory.get("retrieval_date"),
        "source_providers": [s["provider"] for s in inventory.get("sources", [])],
    })
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(_json_bytes(doc))
    return dict(doc["build"])


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Build the offline FH6 official places catalog from reviewed source snapshots.")
    p.add_argument("--graph", type=Path, default=Path("static/data/fh6_navgraph_v1.json.gz"))
    p.add_argument("--output", type=Path, default=Path("static/data/builtin_places.json"))
    p.add_argument("--catalog-version", default="2026.08.29.1")
    args = p.parse_args(argv)
    report = build_official_catalog(graph_path=args.graph, output_path=args.output, catalog_version=args.catalog_version)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
