from __future__ import annotations

import argparse
import json
from pathlib import Path

from catalog_validator import validate_catalogs
from .build import build_official_catalog, load_navgraph
from .curate import enrich_curated_catalog


def validate_scale(builtin_doc: dict, *, recommended_total: int) -> dict:
    runtime_total = len(builtin_doc.get("places") or [])
    build = builtin_doc.get("build") or {}
    reported = int(build.get("reported_source_markers") or 0)
    reason = str(build.get("coverage_limited_reason") or "").strip()
    coverage_limited = reported > runtime_total
    if coverage_limited and not reason:
        raise ValueError("catalog is below reported source scale but coverage_limited_reason is empty")
    return {
        "official_runtime_places": runtime_total,
        "reported_source_markers": reported,
        "recommended_total": int(recommended_total),
        "coverage_limited": coverage_limited,
        "coverage_limited_reason": reason if coverage_limited else "",
    }


def build_release_catalogs(*, graph_path: Path, curated_seed_path: Path, output_dir: Path, catalog_version: str) -> dict:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    builtin_path = output_dir / "builtin_places.json"
    curated_path = output_dir / "scenic_catalog.json"

    official_report = build_official_catalog(
        graph_path=graph_path,
        output_path=builtin_path,
        catalog_version=catalog_version,
    )
    curated_report = enrich_curated_catalog(
        input_path=curated_seed_path,
        graph_path=graph_path,
        output_path=curated_path,
        catalog_version=catalog_version,
    )
    builtin = json.loads(builtin_path.read_text(encoding="utf-8"))
    curated = json.loads(curated_path.read_text(encoding="utf-8"))
    graph = load_navgraph(graph_path)
    validation = validate_catalogs(builtin, curated, graph)
    recommended_total = sum(bool(p.get("default_visible")) for p in (builtin.get("places") or [])) + sum(
        bool(p.get("default_visible")) for p in (curated.get("places") or [])
    )
    scale = validate_scale(builtin, recommended_total=recommended_total)
    return {
        "catalog_version": catalog_version,
        "official": official_report,
        "curated": curated_report,
        "scale": scale,
        "validation": validation,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Build and validate offline FH6 Planner catalogs.")
    p.add_argument("--graph", type=Path, default=Path("static/data/fh6_navgraph_v1.json.gz"))
    p.add_argument("--curated-seed", type=Path, default=Path("static/data/scenic_catalog.json"))
    p.add_argument("--output-dir", type=Path, default=Path("static/data"))
    p.add_argument("--catalog-version", default="2026.08.29.1")
    args = p.parse_args(argv)
    report = build_release_catalogs(
        graph_path=args.graph,
        curated_seed_path=args.curated_seed,
        output_dir=args.output_dir,
        catalog_version=args.catalog_version,
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
