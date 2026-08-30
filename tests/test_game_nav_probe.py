import importlib.util


def test_game_nav_probe_module_exists():
    assert importlib.util.find_spec('game_nav_probe') is not None


def test_score_candidate_function_exists():
    import game_nav_probe as probe
    assert hasattr(probe, 'score_candidate')


def test_score_candidate_prioritizes_navigation_lane_and_junction_paths():
    import game_nav_probe as probe
    score, reasons = probe.score_candidate(r'mediapc\\OpenWorld\\Tokyo\\Navigation\\lane_junction_graph.bin')
    assert score >= 12
    joined = ' '.join(reasons).lower()
    assert 'navigation' in joined
    assert 'lane' in joined
    assert 'junction' in joined


def test_score_candidate_uses_content_hits_but_does_not_promote_unrelated_files_too_high():
    import game_nav_probe as probe
    score, reasons = probe.score_candidate('textures/carpaint.bin', ['oneway', 'traffic'])
    assert 0 < score < 12
    assert any('content' in reason.lower() for reason in reasons)


def test_extract_strings_function_exists():
    import game_nav_probe as probe
    assert hasattr(probe, 'extract_strings')


def test_extract_strings_finds_ascii_and_utf16_navigation_terms_without_garbage():
    import game_nav_probe as probe
    data = b'\x00\x01laneGraph\x00junk\x02' + 'OneWay Junction'.encode('utf-16le') + b'\x00\xff'
    strings = probe.extract_strings(data, min_len=5)
    joined = '\n'.join(strings)
    assert 'laneGraph' in joined
    assert 'OneWay Junction' in joined
    assert all(len(s) >= 5 for s in strings)


def test_parse_steam_libraryfolders_extracts_windows_paths():
    import game_nav_probe as probe
    assert hasattr(probe, 'parse_steam_libraryfolders')
    sample = r'''
"libraryfolders"
{
    "0"
    {
        "path"        "C:\\Program Files (x86)\\Steam"
    }
    "1"
    {
        "path"        "D:\\SteamLibrary"
    }
}
'''
    paths = probe.parse_steam_libraryfolders(sample)
    assert paths == [r'C:\Program Files (x86)\Steam', r'D:\SteamLibrary']


def test_scan_game_root_finds_text_and_binary_navigation_candidates(tmp_path):
    import game_nav_probe as probe
    assert hasattr(probe, 'scan_game_root')

    nav_dir = tmp_path / 'MediaPC' / 'OpenWorld' / 'Tokyo' / 'Navigation'
    nav_dir.mkdir(parents=True)
    (nav_dir / 'junctions.xml').write_text('<Junction OneWay="true" Lane="12"/>', encoding='utf-8')

    misc = tmp_path / 'MediaPC' / 'misc'
    misc.mkdir(parents=True)
    (misc / 'opaque.bin').write_bytes(b'xxxx' + 'TrafficLaneDirection'.encode('utf-16le') + b'yyyy')
    (misc / 'unrelated.bin').write_bytes(b'car paint texture only')

    report = probe.scan_game_root(tmp_path)
    paths = {c['relative_path']: c for c in report['candidates']}
    assert 'MediaPC/OpenWorld/Tokyo/Navigation/junctions.xml' in paths
    assert paths['MediaPC/OpenWorld/Tokyo/Navigation/junctions.xml']['score'] >= 12
    assert 'MediaPC/misc/opaque.bin' in paths
    assert 'direction' in paths['MediaPC/misc/opaque.bin']['matched_content_keywords']
    assert 'MediaPC/misc/unrelated.bin' not in paths
    assert report['stats']['scanned_files'] == 3


def test_looks_like_fh6_root_accepts_media_folder_or_executable(tmp_path):
    import game_nav_probe as probe
    assert hasattr(probe, 'looks_like_fh6_root')
    game = tmp_path / 'Forza Horizon 6'
    game.mkdir()
    assert not probe.looks_like_fh6_root(game)
    (game / 'MediaPC').mkdir()
    assert probe.looks_like_fh6_root(game)


def test_write_reports_creates_shareable_json_text_and_tsv_without_absolute_root(tmp_path):
    import game_nav_probe as probe
    assert hasattr(probe, 'write_reports')
    report = {
        'format': 'fh6-game-nav-asset-probe-v1',
        'game_root_name': 'Forza Horizon 6',
        'stats': {'scanned_files': 10, 'candidate_files': 1, 'unreadable_files': 0, 'sampled_binary_bytes': 50, 'skipped_large_binaries': 0},
        'candidates': [{
            'relative_path': 'MediaPC/OpenWorld/Tokyo/Navigation/lane.bin',
            'size_bytes': 123,
            'extension': '.bin',
            'score': 18,
            'reasons': ['path:navigation', 'path:lane'],
            'matched_content_keywords': ['direction'],
            'text_excerpts': [],
            'sample_strings': ['LaneDirection'],
            'sampled_content': True,
        }],
    }
    paths = probe.write_reports(report, tmp_path)
    assert {p.name for p in paths} == {'fh6_nav_asset_report.json', 'fh6_nav_asset_report.txt', 'fh6_nav_candidates.tsv'}
    combined = '\n'.join(p.read_text(encoding='utf-8') for p in paths)
    assert 'MediaPC/OpenWorld/Tokyo/Navigation/lane.bin' in combined
    assert str(tmp_path.resolve()) not in combined


def test_discover_game_roots_filters_candidates_and_normalizes_xbox_content(tmp_path):
    import game_nav_probe as probe
    assert hasattr(probe, 'discover_game_roots')
    steam = tmp_path / 'Steam' / 'steamapps' / 'common' / 'ForzaHorizon6'
    (steam / 'MediaPC').mkdir(parents=True)
    xbox_parent = tmp_path / 'XboxGames' / 'Forza Horizon 6'
    (xbox_parent / 'Content' / 'MediaPC').mkdir(parents=True)
    bad = tmp_path / 'OtherGame'
    bad.mkdir()
    roots = probe.discover_game_roots(candidates=[steam, xbox_parent, bad])
    assert roots == [steam.resolve(), (xbox_parent / 'Content').resolve()]


def test_create_report_bundle_contains_only_generated_reports(tmp_path):
    import game_nav_probe as probe
    assert hasattr(probe, 'create_report_bundle')
    files = []
    for name in ('fh6_nav_asset_report.json', 'fh6_nav_asset_report.txt', 'fh6_nav_candidates.tsv'):
        p = tmp_path / name
        p.write_text(name, encoding='utf-8')
        files.append(p)
    bundle = probe.create_report_bundle(files, tmp_path)
    assert bundle.name == 'FH6_Game_Nav_Probe_Report.zip'
    import zipfile
    with zipfile.ZipFile(bundle) as zf:
        assert set(zf.namelist()) == {p.name for p in files}


def test_main_scans_explicit_game_folder_and_writes_bundle(tmp_path):
    import game_nav_probe as probe
    assert hasattr(probe, 'main')
    game = tmp_path / 'game'
    nav = game / 'MediaPC' / 'OpenWorld' / 'Tokyo' / 'Navigation'
    nav.mkdir(parents=True)
    (nav / 'lane_graph.xml').write_text('<Lane Direction="forward" Junction="A"/>', encoding='utf-8')
    out = tmp_path / 'out'
    code = probe.main([str(game), '--output', str(out)])
    assert code == 0
    assert (out / 'FH6_Game_Nav_Probe_Report.zip').is_file()
    assert (out / 'fh6_nav_asset_report.json').is_file()


def test_probe_batch_launcher_is_ascii_crlf_and_calls_python_probe():
    from pathlib import Path
    bat = Path(__file__).resolve().parents[1] / 'probe_game_nav_assets.bat'
    assert bat.is_file()
    raw = bat.read_bytes()
    raw.decode('ascii')
    assert b'\r\n' in raw
    assert b'game_nav_probe.py' in raw
