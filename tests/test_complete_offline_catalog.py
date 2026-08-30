import json
from collections import Counter
from pathlib import Path

from tools.places_import.build import build_official_catalog


def test_offline_official_catalog_contains_all_796_inventory_markers(tmp_path):
    output = tmp_path / 'builtin_places.json'
    report = build_official_catalog(
        graph_path=Path('static/data/fh6_navgraph_v1.json.gz'),
        output_path=output,
        catalog_version='test-full-offline',
    )
    doc = json.loads(output.read_text(encoding='utf-8'))
    assert report['runtime_places'] == 796
    assert len(doc['places']) == 796
    assert report['reported_source_markers'] == 796
    assert report['coordinate_records_captured'] == 796
    assert not report.get('coverage_limited_reason')

    counts = Counter(p['category'] for p in doc['places'])
    assert counts['xp_board'] == 200
    assert counts['mascot'] == 200
    assert counts['barn_find'] == 15
    assert counts['treasure_car'] == 9
    assert counts['speed_trap'] == 30
    assert counts['speed_zone'] == 30
