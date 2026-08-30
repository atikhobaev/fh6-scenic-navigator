import json
import math
import struct
import zipfile
from pathlib import Path


def _write_nav(path: Path, size: int, *, floats=()):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = bytearray((i * 37 + 11) % 256 for i in range(size))
    for idx, value in enumerate(floats):
        off = 32 + idx * 4
        if off + 4 <= len(data):
            data[off:off+4] = struct.pack('<f', value)
    path.write_bytes(data)


def test_nav_binary_probe_module_exists():
    import nav_binary_probe  # noqa: F401


def test_select_nav_samples_includes_freeroam_and_route_size_spread(tmp_path):
    import nav_binary_probe as probe
    root = tmp_path / 'game'
    _write_nav(root / 'media/OpenWorld/Brio/Freeroam/Brio_00.nav', 3000)
    sizes = [100, 200, 400, 800, 1600, 3200, 6400]
    for i, size in enumerate(sizes, 1):
        _write_nav(root / f'media/OpenWorld/Brio/AITracks/Route{i}.nav', size)

    selected = probe.select_nav_samples(root, route_count=4)
    rels = [p.relative_to(root).as_posix() for p in selected]
    assert rels[0] == 'media/OpenWorld/Brio/Freeroam/Brio_00.nav'
    route_sizes = [p.stat().st_size for p in selected[1:]]
    assert len(route_sizes) == 4
    assert route_sizes == sorted(set(route_sizes))
    assert route_sizes[0] == 100
    assert route_sizes[-1] == 6400
    assert any(200 <= size <= 800 for size in route_sizes[1:-1])
    assert any(800 <= size <= 3200 for size in route_sizes[1:-1])


def test_hexdump_is_offset_annotated_and_bounded():
    import nav_binary_probe as probe
    dump = probe.hexdump(bytes(range(64)), limit=32)
    assert '00000000' in dump
    assert '00000010' in dump
    assert '00000020' not in dump
    assert '00 01 02 03' in dump


def test_entropy_distinguishes_repetitive_and_varied_data():
    import nav_binary_probe as probe
    low = probe.shannon_entropy(b'\x00' * 4096)
    high = probe.shannon_entropy(bytes(range(256)) * 16)
    assert low == 0.0
    assert high > 7.9


def test_float32_summary_detects_finite_worldlike_values(tmp_path):
    import nav_binary_probe as probe
    path = tmp_path / 'sample.nav'
    _write_nav(path, 256, floats=[0.0, 12.5, -88.25, 4096.0, 1e20, float('nan')])
    summary = probe.float32_summary(path.read_bytes())
    assert summary['total_aligned_values'] >= 6
    assert summary['finite_values'] >= 4
    assert summary['moderate_abs_le_100000'] >= 4
    assert summary['nonfinite_values'] >= 1


def test_candidate_record_strides_reports_divisible_payloads():
    import nav_binary_probe as probe
    result = probe.candidate_record_strides(1024, offsets=(0, 16), strides=(8, 12, 16, 24, 32))
    assert {'offset': 0, 'stride': 16, 'records': 64} in result
    assert {'offset': 16, 'stride': 24, 'records': 42} in result


def test_analyze_nav_file_returns_hash_header_tail_entropy_and_strings(tmp_path):
    import nav_binary_probe as probe
    path = tmp_path / 'Route1.nav'
    payload = b'NAVHDR\x00LaneDirection\x00' + bytes(range(128)) + b'ENDNAV'
    path.write_bytes(payload)
    analysis = probe.analyze_nav_file(path)
    assert analysis['size_bytes'] == len(payload)
    assert len(analysis['sha256']) == 64
    assert '00000000' in analysis['header_hexdump']
    assert analysis['tail_hexdump']
    assert isinstance(analysis['entropy_bits_per_byte'], float)
    assert any('LaneDirection' in s for s in analysis['strings'])
    assert 'float32' in analysis
    assert 'record_stride_candidates' in analysis


def test_build_nav_probe_bundle_contains_reports_and_actual_nav_samples(tmp_path):
    import nav_binary_probe as probe
    root = tmp_path / 'ForzaHorizon6'
    _write_nav(root / 'media/OpenWorld/Brio/Freeroam/Brio_00.nav', 3000)
    for i, size in enumerate([100, 500, 1500, 4000, 8000], 1):
        _write_nav(root / f'media/OpenWorld/Brio/AITracks/Route{i}.nav', size)
    out = tmp_path / 'out'
    bundle = probe.build_nav_probe_bundle(root, out, route_count=4)
    assert bundle.name == 'FH6_NAV_Binary_Probe.zip'
    assert bundle.is_file()
    with zipfile.ZipFile(bundle) as zf:
        names = set(zf.namelist())
        assert 'nav_binary_report.json' in names
        assert 'nav_binary_report.txt' in names
        sample_names = [n for n in names if n.startswith('samples/') and n.endswith('.nav')]
        assert len(sample_names) == 5
        report = json.loads(zf.read('nav_binary_report.json'))
        assert report['format'] == 'fh6-nav-binary-probe-v1'
        assert len(report['samples']) == 5
        assert any(s['relative_path'].endswith('Brio_00.nav') for s in report['samples'])


def test_nav_binary_probe_batch_launcher_is_ascii_crlf_and_calls_probe():
    bat = Path(__file__).resolve().parents[1] / 'probe_nav_binary_samples.bat'
    assert bat.is_file()
    raw = bat.read_bytes()
    raw.decode('ascii')
    assert b'\r\n' in raw
    assert b'nav_binary_probe.py' in raw
