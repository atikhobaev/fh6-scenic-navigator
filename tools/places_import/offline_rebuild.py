"""Rebuild FH6 Planner catalogs exclusively from release-owned local data."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile

from .build import load_source_inventory
from .release_build import build_release_catalogs

_STAGE_LABELS = (
    "[1/5] Checking bundled source snapshots...",
    "[2/5] Checking bundled Directed WVAN graph...",
    "[3/5] Building and snapping local Planner catalogs...",
    "[4/5] Validating rebuilt catalogs...",
    "[5/5] Publishing rebuilt catalogs atomically...",
)


def _stage(index: int) -> None:
    print(_STAGE_LABELS[index - 1], flush=True)


def rebuild_offline_catalogs(*, root: Path, catalog_version: str = "2026.08.30.v1.17.2") -> dict:
    root = Path(root).resolve()
    data_dir = root / "static" / "data"
    graph_path = data_dir / "fh6_navgraph_v1.json.gz"
    roads_path = data_dir / "fh6_roads.json"
    curated_path = data_dir / "scenic_catalog.json"

    _stage(1)
    inventory = load_source_inventory()
    captured = int(inventory.get("coordinate_records_captured") or 0)
    if captured <= 0:
        raise RuntimeError("bundled source inventory contains no positioned records")
    quality = inventory.get("coordinate_quality") or {}
    exact = int(quality.get("source_exact") or 0)
    proxy = int(quality.get("road_network_proxy") or 0)
    detail = f" ({exact} source-exact + {proxy} road-geometry proxy)" if exact or proxy else ""
    print(f"      OK: {captured} bundled marker records are stored locally{detail}.", flush=True)

    _stage(2)
    if not graph_path.is_file() or graph_path.stat().st_size <= 0:
        raise RuntimeError(f"bundled Directed WVAN graph is missing: {graph_path}")
    if not roads_path.is_file() or roads_path.stat().st_size <= 0:
        raise RuntimeError(f"bundled FH6 road dataset is missing: {roads_path}. Re-extract the release ZIP.")
    try:
        roads_doc = json.loads(roads_path.read_text(encoding="utf-8"))
        road_count = len(roads_doc.get("roads") or [])
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"bundled FH6 road dataset is unreadable: {exc}") from exc
    if road_count <= 0:
        raise RuntimeError("bundled FH6 road dataset is empty")
    if not curated_path.is_file():
        raise RuntimeError(f"bundled curated catalog is missing: {curated_path}")
    print(
        f"      OK: local Directed WVAN graph ({graph_path.stat().st_size:,} bytes) + {road_count} road records.",
        flush=True,
    )

    data_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".fh6_catalog_build_", dir=root) as td:
        tmp_dir = Path(td)
        _stage(3)
        report = build_release_catalogs(
            graph_path=graph_path,
            curated_seed_path=curated_path,
            output_dir=tmp_dir,
            catalog_version=catalog_version,
        )
        official = int(report["official"]["runtime_places"])
        curated = int(report["curated"]["snapped_places"])
        print(f"      OK: built {official} game POIs + {curated} curated places.", flush=True)

        _stage(4)
        validation = report.get("validation") or {}
        if not validation.get("valid"):
            raise RuntimeError("rebuilt catalog validation failed")
        print(f"      OK: {validation.get('places', 0)} total places passed validation.", flush=True)

        _stage(5)
        names = ("builtin_places.json", "scenic_catalog.json")
        staged: dict[str, Path] = {}
        previous: dict[str, bytes | None] = {}
        for name in names:
            src = tmp_dir / name
            if not src.is_file():
                raise RuntimeError(f"rebuilder did not produce {name}")
            dest = data_dir / name
            previous[name] = dest.read_bytes() if dest.is_file() else None
            staging = data_dir / f".{name}.new"
            shutil.copyfile(src, staging)
            staged[name] = staging
        try:
            for name in names:
                os.replace(staged[name], data_dir / name)
        except Exception:
            # Publication spans two JSON files. Restore every previous file so a
            # mid-publish failure cannot leave a mixed-version catalog pair.
            for name in names:
                dest = data_dir / name
                old = previous[name]
                if old is None:
                    try:
                        dest.unlink()
                    except FileNotFoundError:
                        pass
                else:
                    dest.write_bytes(old)
            raise
        finally:
            for staging in staged.values():
                try:
                    staging.unlink()
                except FileNotFoundError:
                    pass
        print("      OK: local catalogs published with rollback protection. Internet was not used.", flush=True)

    return {
        "status": "rebuilt",
        "internet_used": False,
        "catalog_version": catalog_version,
        "official_places": int(report["official"]["runtime_places"]),
        "curated_places": int(report["curated"]["snapped_places"]),
        "total_places": int(report["validation"]["places"]),
        "road_records": road_count,
        "coverage_limited": bool(report["scale"]["coverage_limited"]),
        "coverage_limited_reason": report["scale"].get("coverage_limited_reason") or "",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Rebuild FH6 Planner catalogs from bundled local snapshots only.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--catalog-version", default="2026.08.30.v1.17.2")
    args = parser.parse_args(argv)
    try:
        result = rebuild_offline_catalogs(root=args.root, catalog_version=args.catalog_version)
    except Exception as exc:
        print(f"ERROR: {exc}", flush=True)
        print("Existing published catalog files were kept whenever publication had not started.", flush=True)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
