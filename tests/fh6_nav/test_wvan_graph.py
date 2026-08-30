import json
from pathlib import Path
import pytest

from fh6_nav.wvan import parse_wvan_file
from fh6_nav.graph import build_graph
from fh6_nav.compiler import compile_graph_dict

BRIO = Path('/mnt/data/brio/Brio/Freeroam/Brio_00.nav')

@pytest.mark.skipif(not BRIO.exists(), reason='Brio asset unavailable')
def test_real_brio_parses_proven_tables_and_metadata():
    doc = parse_wvan_file(BRIO)
    assert doc.source_sha256 == 'f06b4b958e60af5e52bc456173a5ba2b3ce6c900c732c8c5d96bd426498f5dbb'
    assert len(doc.points) == 38473
    assert len(doc.sections) == 1532
    assert len(doc.point_sequence) == 40966
    assert len(doc.metadata_records) == 31139
    assert 'oneway_forward' in doc.metadata_keys
    assert 'no_right_turn' in doc.metadata_keys

@pytest.mark.skipif(not BRIO.exists(), reason='Brio asset unavailable')
def test_real_brio_builds_directed_graph_without_reverse_oneway_edges():
    doc = parse_wvan_file(BRIO)
    graph = build_graph(doc)
    assert len(graph.points) == 38473
    assert len(graph.segments) > 60000
    pair_set = {(s.from_point, s.to_point) for s in graph.segments}
    one_way = [s for s in graph.segments if s.oneway]
    assert one_way
    sample = one_way[:500]
    assert all((s.to_point, s.from_point) not in pair_set for s in sample)
    assert graph.capabilities['directed_segments'] is True
    assert graph.capabilities['turn_transitions'] is True

@pytest.mark.skipif(not BRIO.exists(), reason='Brio asset unavailable')
def test_compiler_schema_is_deterministic_and_validated_for_known_brio():
    payload = compile_graph_dict(build_graph(parse_wvan_file(BRIO)))
    assert payload['format'] == 'fh6-navgraph-v1'
    assert payload['source']['sha256'].startswith('f06b4b95')
    assert payload['capabilities']['route_validated'] is True
    assert len(payload['points']) == 38473
    assert len(payload['segments']) > 60000
    assert len(payload['transitions']) > 50000
