import json
from pathlib import Path

import pytest

from tools.places_import.models import RawPlace
from tools.places_import.normalize import normalize_text, stable_place_id, lab_map_ref_to_world
from tools.places_import.dedupe import dedupe_places
from tools.places_import.build_catalog import build_runtime_catalog


def test_normalize_text_and_stable_id_are_deterministic():
    assert normalize_text("  Hakone Nanamagari! ") == "hakone nanamagari"
    assert stable_place_id("game", "Treasure Car", "1985 Mazda RX-7 GSL-SE") == "builtin.game.treasure_car.1985_mazda_rx_7_gsl_se"


def test_labs_map_reference_transform_matches_existing_navigator_calibration():
    # DamnModz/LabsGG map ref 589,1465 is a source-labeled FH6 image coordinate.
    x, z = lab_map_ref_to_world(589, 1465)
    assert x == pytest.approx(-4327.052, abs=0.5)
    assert z == pytest.approx(-1100.972, abs=0.5)


def test_dedupe_merges_aliases_and_provenance_without_losing_position():
    a = RawPlace(
        provider="damnmodz",
        source_id="treasure-1",
        name="1985 Mazda RX-7 GSL-SE",
        category="treasure_car",
        map_x=589,
        map_y=1465,
        aliases=("Mazda RX7 Treasure",),
        provenance=("https://example.test/a",),
    )
    b = RawPlace(
        provider="mapmaster",
        source_id="tc-rx7",
        name="1985 Mazda RX-7 GSL-SE",
        category="treasure_car",
        aliases=("Mazda RX-7",),
        provenance=("https://example.test/b",),
    )
    merged = dedupe_places([a, b])
    assert len(merged) == 1
    p = merged[0]
    assert p.map_x == 589 and p.map_y == 1465
    assert set(p.aliases) == {"Mazda RX7 Treasure", "Mazda RX-7"}
    assert {s.provider for s in p.sources} == {"damnmodz", "mapmaster"}


def test_runtime_catalog_excludes_records_without_proven_coordinate_transform():
    positioned = RawPlace("damnmodz", "one", "Place One", "landmark", map_x=589, map_y=1465)
    unpositioned = RawPlace("mapmaster", "two", "Place Two", "landmark")
    doc = build_runtime_catalog([positioned, unpositioned], catalog_version="test")
    assert [p["name"] for p in doc["places"]] == ["Place One"]
    assert doc["build"]["excluded_unpositioned"] == 1


def test_source_snapshot_has_two_independent_sources_and_no_descriptions():
    snapshot = json.loads(Path("tools/places_import/snapshots/source_evidence.json").read_text(encoding="utf-8"))
    assert {s["provider"] for s in snapshot["sources"]} >= {"damnmodz", "mapmaster"}
    assert all("description" not in row for row in snapshot["records"])


def test_damnmodz_snapshot_adapter_loads_all_crosschecked_hidden_cars_with_map_refs():
    from tools.places_import.sources.damnmodz import load_snapshot

    rows = load_snapshot()
    assert len(rows) == 24
    assert {p.category for p in rows} == {"barn_find", "treasure_car"}
    assert all(p.map_x is not None and p.map_y is not None for p in rows)
    assert all(p.sources[0].provider == "damnmodz" for p in rows)
    assert any(p.name == "1991 Mazda #55 Mazda 787B" and p.map_x == 1451 and p.map_y == 558 for p in rows)


def test_mapmaster_snapshot_adapter_independently_corroborates_same_24_hidden_cars():
    from tools.places_import.sources.mapmaster import load_snapshot

    rows = load_snapshot()
    assert len(rows) == 24
    assert {p.category for p in rows} == {"barn_find", "treasure_car"}
    assert all(p.map_x is None and p.map_y is None for p in rows)
    assert all(p.sources[0].provider == "mapmaster" for p in rows)
    assert {normalize_text(p.name) for p in rows} == {
        normalize_text(p.name)
        for p in __import__("tools.places_import.sources.damnmodz", fromlist=["load_snapshot"]).load_snapshot()
    }


def test_cross_source_hidden_car_build_deduplicates_to_24_reviewed_runtime_places():
    from tools.places_import.sources.damnmodz import load_snapshot as load_damnmodz
    from tools.places_import.sources.mapmaster import load_snapshot as load_mapmaster

    doc = build_runtime_catalog([*load_damnmodz(), *load_mapmaster()], catalog_version="hidden-cars-test")
    assert len(doc["places"]) == 24
    assert doc["build"]["input_records"] == 48
    assert doc["build"]["deduplicated_records"] == 24
    assert all(p["quality"] == "reviewed" for p in doc["places"])
    assert all({s["provider"] for s in p["sources"]} == {"damnmodz", "mapmaster"} for p in doc["places"])


def test_navgraph_snapper_finds_nearest_point_and_uses_graph_y():
    from tools.places_import.snap import NavGraphSnapper

    graph = {
        "format": "fh6-navgraph-v1",
        "capabilities": {"route_validated": True},
        "points": [[10, 0.0, 3.0, 0.0], [11, 100.0, 7.0, 0.0], [12, 0.0, 9.0, 100.0]],
        "segments": [],
        "transitions": [],
    }
    snapper = NavGraphSnapper(graph, cell_size=50.0)
    hit = snapper.nearest(96.0, 3.0)
    assert hit.point_id == 11
    assert hit.y == pytest.approx(7.0)
    assert hit.distance_m == pytest.approx(5.0)
    assert hit.route_validated is True


def test_runtime_catalog_with_navgraph_sets_anchor_y_distance_and_conservative_quality():
    from tools.places_import.snap import NavGraphSnapper

    graph = {
        "format": "fh6-navgraph-v1",
        "capabilities": {"route_validated": True},
        "points": [[77, -4327.0, 123.0, -1101.0]],
        "segments": [],
        "transitions": [],
    }
    positioned = RawPlace(
        "damnmodz", "one", "Place One", "landmark", map_x=589, map_y=1465,
        sources=(
            __import__("tools.places_import.models", fromlist=["SourceRef"]).SourceRef("damnmodz", "one"),
            __import__("tools.places_import.models", fromlist=["SourceRef"]).SourceRef("mapmaster", "one-mm"),
        ),
    )
    doc = build_runtime_catalog([positioned], catalog_version="test", snapper=NavGraphSnapper(graph))
    p = doc["places"][0]
    assert p["position"]["y"] == pytest.approx(123.0)
    assert p["navigation"]["anchor_point_id"] == 77
    assert p["navigation"]["snap_distance_m"] < 1.0
    assert p["navigation"]["route_validated"] is True
    assert p["quality"] == "verified"


def test_large_snap_distance_is_kept_but_hidden_from_recommended_catalog():
    from tools.places_import.snap import NavGraphSnapper

    graph = {"format":"fh6-navgraph-v1","capabilities":{"route_validated":True},"points":[[1,0.0,2.0,0.0]],"segments":[],"transitions":[]}
    p = RawPlace("damnmodz","far","Far Place","landmark",world_x=900.0,world_z=0.0)
    doc = build_runtime_catalog([p], catalog_version="test", snapper=NavGraphSnapper(graph))
    row = doc["places"][0]
    assert row["quality"] == "unverified"
    assert row["default_visible"] is False
    assert row["navigation"]["snap_distance_m"] == pytest.approx(900.0)


def test_full_hub_snapshot_contains_all_796_positioned_markers_in_38_categories():
    from tools.places_import.sources.forzahorizonhub import load_snapshot

    rows = load_snapshot()
    assert len(rows) == 796
    assert len({(r.provider, r.source_id) for r in rows}) == 796
    assert all(r.world_x is not None and r.world_z is not None for r in rows)
    assert len({r.tags[0] for r in rows if r.tags}) == 38


def test_source_inventory_declares_offline_bundled_coordinate_snapshot():
    inv = json.loads(Path("tools/places_import/snapshots/source_inventory.json").read_text(encoding="utf-8"))
    assert inv["reported_marker_upper_bound"] == 796
    assert inv["coordinate_records_captured"] == 796
    assert inv.get("coverage_limited_reason") == ""
    assert inv["coordinate_quality"]["source_exact"] == 24
    assert inv["coordinate_quality"]["road_network_proxy"] == 772
    assert any(s["provider"] == "forzahorizonhub" and s["reported_markers"] == 796 and s["reported_categories"] == 38 for s in inv["sources"])
    assert all("description" not in source for source in inv["sources"])


def test_official_catalog_build_is_byte_deterministic_and_uses_real_navgraph(tmp_path):
    from tools.places_import.build import build_official_catalog

    graph_path = Path("static/data/fh6_navgraph_v1.json.gz")
    out1 = tmp_path / "one.json"
    out2 = tmp_path / "two.json"
    r1 = build_official_catalog(graph_path=graph_path, output_path=out1, catalog_version="test-1")
    r2 = build_official_catalog(graph_path=graph_path, output_path=out2, catalog_version="test-1")
    assert out1.read_bytes() == out2.read_bytes()
    doc = json.loads(out1.read_text(encoding="utf-8"))
    assert r1 == r2 == doc["build"]
    assert len(doc["places"]) == 796
    assert all(p["navigation"]["anchor_point_id"] is not None for p in doc["places"])
    assert doc["build"]["reported_source_markers"] == 796
    assert doc["build"]["coordinate_records_captured"] == 796
    assert doc["build"]["coverage_limited_reason"] == ""

def test_curated_catalog_enrichment_snaps_all_existing_places_without_changing_ids(tmp_path):
    from tools.places_import.curate import enrich_curated_catalog

    src = Path("static/data/scenic_catalog.json")
    before = json.loads(src.read_text(encoding="utf-8"))
    out = tmp_path / "scenic.json"
    report = enrich_curated_catalog(
        input_path=src,
        graph_path=Path("static/data/fh6_navgraph_v1.json.gz"),
        output_path=out,
        catalog_version="curated-test",
    )
    after = json.loads(out.read_text(encoding="utf-8"))
    assert [p["id"] for p in after["places"]] == [p["id"] for p in before["places"]]
    assert len(after["places"]) == 27
    assert report["snapped_places"] == 27
    assert all(p["navigation"]["anchor_point_id"] is not None for p in after["places"])
    assert all(p["position"]["y"] != 0.0 for p in after["places"])


def test_built_catalogs_pass_runtime_catalog_validator(tmp_path):
    from catalog_validator import validate_catalogs
    from tools.places_import.build import build_official_catalog, load_navgraph
    from tools.places_import.curate import enrich_curated_catalog

    graph_path = Path("static/data/fh6_navgraph_v1.json.gz")
    builtin_path = tmp_path / "builtin.json"
    curated_path = tmp_path / "curated.json"
    build_official_catalog(graph_path=graph_path, output_path=builtin_path, catalog_version="test")
    enrich_curated_catalog(
        input_path=Path("static/data/scenic_catalog.json"),
        graph_path=graph_path,
        output_path=curated_path,
        catalog_version="test",
    )
    result = validate_catalogs(
        json.loads(builtin_path.read_text(encoding="utf-8")),
        json.loads(curated_path.read_text(encoding="utf-8")),
        load_navgraph(graph_path),
    )
    assert result["valid"] is True
    assert result["places"] == 823


def test_release_catalog_build_writes_both_catalogs_and_validation_report(tmp_path):
    from tools.places_import.release_build import build_release_catalogs

    report = build_release_catalogs(
        graph_path=Path("static/data/fh6_navgraph_v1.json.gz"),
        curated_seed_path=Path("static/data/scenic_catalog.json"),
        output_dir=tmp_path,
        catalog_version="release-test",
    )
    assert (tmp_path / "builtin_places.json").is_file()
    assert (tmp_path / "scenic_catalog.json").is_file()
    assert report["validation"]["valid"] is True
    assert report["validation"]["places"] == 823
    assert report["official"]["runtime_places"] == 796
    assert report["curated"]["snapped_places"] == 27
    assert report["scale"]["coverage_limited"] is False
    assert report["scale"]["coverage_limited_reason"] == ""


def test_catalog_scale_gate_requires_explicit_limitation_below_web_reported_scale(tmp_path):
    from tools.places_import.release_build import validate_scale

    limited = {
        "places": [{"id": f"p{i}", "default_visible": True} for i in range(24)],
        "build": {"reported_source_markers": 880, "coverage_limited_reason": "coordinates unavailable for bulk reuse"},
    }
    assert validate_scale(limited, recommended_total=51)["coverage_limited"] is True
    broken = {"places": limited["places"], "build": {"reported_source_markers": 880, "coverage_limited_reason": ""}}
    with pytest.raises(ValueError, match="coverage_limited_reason"):
        validate_scale(broken, recommended_total=51)


def test_curated_enrichment_seeds_grand_tour_loop_and_collection_with_legal_directed_paths(tmp_path):
    from tools.places_import.curate import enrich_curated_catalog
    from tools.places_import.build import load_navgraph
    from catalog_validator import validate_catalogs

    out = tmp_path / "curated.json"
    enrich_curated_catalog(
        input_path=Path("static/data/scenic_catalog.json"),
        graph_path=Path("static/data/fh6_navgraph_v1.json.gz"),
        output_path=out,
        catalog_version="loop-test",
    )
    doc = json.loads(out.read_text(encoding="utf-8"))
    loop = next(b for b in doc["blocks"] if b["id"] == "curated.loop.grand_tour_japan")
    assert loop["type"] == "loop"
    assert loop["reversible"] is True
    assert len(loop["clockwise_anchor_point_ids"]) > 27
    assert len(loop["counterclockwise_anchor_point_ids"]) > 27
    assert loop["clockwise_anchor_point_ids"][0] == loop["clockwise_anchor_point_ids"][-1]
    assert loop["counterclockwise_anchor_point_ids"][0] == loop["counterclockwise_anchor_point_ids"][-1]
    collection = next(c for c in doc["collections"] if c["id"] == "curated.collection.grand_tour_destinations")
    assert collection["place_ids"] == [p["id"] for p in doc["places"]]
    result = validate_catalogs({"schema_version":1,"places":[]}, doc, load_navgraph(Path("static/data/fh6_navgraph_v1.json.gz")))
    assert result["valid"] is True

from tools.places_import.models import RawPlace
from tools.places_import.dedupe import dedupe_places
from tools.places_import.build_catalog import build_runtime_catalog

def test_same_provider_generic_markers_keep_distinct_source_ids_and_runtime_ids():
    rows=[
      RawPlace(provider='mapgenie',source_id='101',name='XP Board',category='xp_board',world_x=0,world_z=0),
      RawPlace(provider='mapgenie',source_id='102',name='XP Board',category='xp_board',world_x=500,world_z=500),
    ]
    merged=dedupe_places(rows)
    assert len(merged)==2
    doc=build_runtime_catalog(rows,catalog_version='test')
    assert len(doc['places'])==2
    assert len({p['id'] for p in doc['places']})==2
