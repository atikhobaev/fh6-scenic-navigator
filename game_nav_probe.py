"""Read-only FH6 game navigation asset probe.

The probe never writes to the game directory. It only inventories files,
extracts small text/binary samples, and writes reports beside this script.
"""

from __future__ import annotations

import argparse
import json
import os
import zipfile
import re
import sys
from pathlib import Path
from typing import Iterable

_PATH_KEYWORDS = {
    'navigation': 6,
    'nav': 5,
    'lane': 5,
    'junction': 5,
    'intersection': 5,
    'oneway': 6,
    'one_way': 6,
    'traffic': 4,
    'route': 4,
    'direction': 4,
    'spline': 3,
    'road': 2,
    'drive': 2,
    'ai': 2,
}

_CONTENT_KEYWORDS = (
    'oneway', 'one_way', 'one-way', 'lane', 'lanes', 'junction', 'intersection',
    'navigation', 'navmesh', 'traffic', 'roadlink', 'road_link', 'transition',
    'turnrestriction', 'turn_restriction', 'direction', 'route', 'spline',
    'driveline', 'roadgraph', 'road_graph', 'link',
)

_TEXT_EXTENSIONS = {
    '.xml', '.json', '.txt', '.ini', '.cfg', '.csv', '.yaml', '.yml', '.lua',
    '.js', '.ts', '.md', '.vdf', '.toml', '.properties', '.manifest', '.config',
}

# Large game packages are not read in full. We take bounded samples instead.
DEFAULT_SAMPLE_BYTES = 768 * 1024
DEFAULT_MAX_BINARY_FILE = 128 * 1024 * 1024
DEFAULT_BINARY_SCAN_BUDGET = 384 * 1024 * 1024


def _keyword_in_path(path: str, keyword: str) -> bool:
    normalized = path.lower().replace('\\', '/').replace('-', '_')
    if keyword == 'ai':
        return bool(re.search(r'(^|[/_.])ai([/_.]|$)', normalized))
    if keyword == 'nav':
        return bool(re.search(r'(^|[/_.])nav(igation)?([/_.]|$)', normalized))
    return keyword in normalized


def score_candidate(rel_path, text_hits=()):
    """Return a deterministic candidate score and human-readable reasons."""
    score = 0
    reasons = []
    for keyword, weight in _PATH_KEYWORDS.items():
        if _keyword_in_path(str(rel_path), keyword):
            score += weight
            reasons.append(f'path:{keyword}')
    seen = set()
    for hit in text_hits or ():
        keyword = str(hit).lower().strip()
        if not keyword or keyword in seen:
            continue
        seen.add(keyword)
        score += 2 if keyword in {'oneway', 'one_way', 'one-way', 'lane', 'lanes', 'junction', 'intersection', 'direction', 'turnrestriction', 'turn_restriction'} else 1
        reasons.append(f'content:{keyword}')
    return score, reasons


def extract_strings(data: bytes, min_len: int = 5):
    """Extract readable ASCII and UTF-16LE strings from a binary sample."""
    if not data:
        return []
    min_len = max(3, int(min_len))
    found = []
    seen = set()

    ascii_pattern = re.compile(rb"[\x20-\x7e]{%d,}" % min_len)
    for match in ascii_pattern.finditer(data):
        text = match.group().decode('ascii', errors='ignore').strip()
        if len(text) >= min_len and text not in seen:
            seen.add(text)
            found.append(text)

    utf16_pattern = re.compile(rb"(?:[\x20-\x7e]\x00){%d,}" % min_len)
    for match in utf16_pattern.finditer(data):
        text = match.group().decode('utf-16le', errors='ignore').strip()
        if len(text) >= min_len and text not in seen:
            seen.add(text)
            found.append(text)

    return found


def parse_steam_libraryfolders(text: str):
    """Parse Steam libraryfolders.vdf path entries without external deps."""
    paths = []
    for match in re.finditer(r'"path"\s*"([^"]+)"', text or '', flags=re.IGNORECASE):
        value = match.group(1).replace('\\\\', '\\')
        if value not in paths:
            paths.append(value)
    return paths


def _content_hits(strings: Iterable[str]) -> list[str]:
    joined = '\n'.join(strings).lower().replace('-', '_')
    hits = []
    for keyword in _CONTENT_KEYWORDS:
        normalized = keyword.replace('-', '_')
        if normalized in joined and normalized not in hits:
            hits.append(normalized)
    return hits


def _relevant_strings(strings: Iterable[str], limit: int = 24) -> list[str]:
    result = []
    for value in strings:
        low = value.lower().replace('-', '_')
        if any(keyword.replace('-', '_') in low for keyword in _CONTENT_KEYWORDS):
            cleaned = value.strip().replace('\x00', '')
            if cleaned and cleaned not in result:
                result.append(cleaned[:280])
        if len(result) >= limit:
            break
    return result


def _read_bounded_sample(path: Path, file_size: int, sample_bytes: int) -> bytes:
    """Read bounded first/middle/last chunks without loading a package into memory."""
    if file_size <= sample_bytes:
        return path.read_bytes()
    chunk = max(4096, sample_bytes // 3)
    parts = []
    with path.open('rb') as fh:
        parts.append(fh.read(chunk))
        middle = max(0, file_size // 2 - chunk // 2)
        fh.seek(middle)
        parts.append(fh.read(chunk))
        fh.seek(max(0, file_size - chunk))
        parts.append(fh.read(chunk))
    return b'\n'.join(parts)


def _text_excerpts(text: str, limit: int = 16) -> list[str]:
    excerpts = []
    for line in text.splitlines():
        low = line.lower().replace('-', '_')
        if any(keyword.replace('-', '_') in low for keyword in _CONTENT_KEYWORDS):
            stripped = line.strip()
            if stripped and stripped not in excerpts:
                excerpts.append(stripped[:360])
        if len(excerpts) >= limit:
            break
    return excerpts


def scan_game_root(
    root,
    *,
    sample_bytes: int = DEFAULT_SAMPLE_BYTES,
    max_binary_file: int = DEFAULT_MAX_BINARY_FILE,
    binary_scan_budget: int = DEFAULT_BINARY_SCAN_BUDGET,
):
    """Scan an FH6 installation read-only and return a JSON-serializable report."""
    root = Path(root).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f'Game folder does not exist: {root}')

    candidates = []
    scanned_files = 0
    unreadable_files = 0
    sampled_binary_bytes = 0
    skipped_large_binaries = 0

    for path in sorted(root.rglob('*')):
        if not path.is_file():
            continue
        scanned_files += 1
        try:
            rel = path.relative_to(root).as_posix()
            size = path.stat().st_size
        except OSError:
            unreadable_files += 1
            continue

        path_score, path_reasons = score_candidate(rel)
        ext = path.suffix.lower()
        hits = []
        excerpts = []
        sample_strings = []
        sampled = False

        try:
            if ext in _TEXT_EXTENSIONS:
                data = _read_bounded_sample(path, size, sample_bytes)
                sampled = True
                text = data.decode('utf-8', errors='ignore')
                hits = _content_hits([text])
                excerpts = _text_excerpts(text)
            elif size <= max_binary_file and sampled_binary_bytes < binary_scan_budget:
                data = _read_bounded_sample(path, size, sample_bytes)
                sampled_binary_bytes += len(data)
                sampled = True
                strings = extract_strings(data)
                hits = _content_hits(strings)
                sample_strings = _relevant_strings(strings)
            elif size > max_binary_file:
                skipped_large_binaries += 1
        except (OSError, PermissionError):
            unreadable_files += 1

        score, reasons = score_candidate(rel, hits)
        if score <= 0:
            continue

        candidates.append({
            'relative_path': rel,
            'size_bytes': size,
            'extension': ext,
            'score': score,
            'reasons': reasons,
            'matched_content_keywords': hits,
            'text_excerpts': excerpts,
            'sample_strings': sample_strings,
            'sampled_content': sampled,
        })

    candidates.sort(key=lambda item: (-item['score'], item['relative_path'].lower()))
    return {
        'format': 'fh6-game-nav-asset-probe-v1',
        'game_root_name': root.name,
        'stats': {
            'scanned_files': scanned_files,
            'candidate_files': len(candidates),
            'unreadable_files': unreadable_files,
            'sampled_binary_bytes': sampled_binary_bytes,
            'skipped_large_binaries': skipped_large_binaries,
        },
        'candidates': candidates,
    }


def looks_like_fh6_root(path) -> bool:
    path = Path(path)
    if not path.is_dir():
        return False
    if any((path / name).is_dir() for name in ('MediaPC', 'mediapc', 'media', 'Media')):
        return True
    for name in ('ForzaHorizon6.exe', 'ForzaHorizon6_Steam.exe', 'ForzaHorizon6.exe'):  # harmless duplicates avoided by any()
        if (path / name).is_file():
            return True
    content = path / 'Content'
    if content.is_dir() and any((content / name).is_dir() for name in ('MediaPC', 'mediapc', 'media', 'Media')):
        return True
    return False


def write_reports(report: dict, output_dir):
    """Write shareable reports containing relative paths only."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / 'fh6_nav_asset_report.json'
    txt_path = output_dir / 'fh6_nav_asset_report.txt'
    tsv_path = output_dir / 'fh6_nav_candidates.tsv'

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

    stats = report.get('stats', {})
    lines = [
        'FH6 GAME NAV ASSET PROBE',
        '========================',
        f"Game root: {report.get('game_root_name', 'unknown')}",
        f"Scanned files: {stats.get('scanned_files', 0)}",
        f"Candidates: {stats.get('candidate_files', 0)}",
        f"Unreadable files: {stats.get('unreadable_files', 0)}",
        f"Skipped large binaries: {stats.get('skipped_large_binaries', 0)}",
        '',
        'TOP CANDIDATES',
        '--------------',
    ]
    for idx, item in enumerate(report.get('candidates', []), 1):
        lines.append(f"{idx:03d}. score={item.get('score', 0):>3}  {item.get('relative_path', '')}")
        if item.get('reasons'):
            lines.append('     reasons: ' + ', '.join(item['reasons']))
        if item.get('matched_content_keywords'):
            lines.append('     content: ' + ', '.join(item['matched_content_keywords']))
        for excerpt in (item.get('text_excerpts') or [])[:5]:
            lines.append('     text: ' + excerpt)
        for value in (item.get('sample_strings') or [])[:5]:
            lines.append('     string: ' + value)
    txt_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    tsv_lines = ['score\trelative_path\tsize_bytes\treasons\tcontent_keywords']
    for item in report.get('candidates', []):
        tsv_lines.append('\t'.join([
            str(item.get('score', 0)),
            str(item.get('relative_path', '')).replace('\t', ' '),
            str(item.get('size_bytes', 0)),
            ','.join(item.get('reasons') or []),
            ','.join(item.get('matched_content_keywords') or []),
        ]))
    tsv_path.write_text('\n'.join(tsv_lines) + '\n', encoding='utf-8')
    return [json_path, txt_path, tsv_path]


def _default_install_candidates():
    """Return common Steam/Xbox FH6 install locations without scanning whole drives."""
    candidates = []
    env_path = os.environ.get('FH6_PATH')
    if env_path:
        candidates.append(Path(env_path))

    steam_roots = []
    for key in ('PROGRAMFILES(X86)', 'PROGRAMFILES'):
        base = os.environ.get(key)
        if base:
            steam_roots.append(Path(base) / 'Steam')
    steam_roots.append(Path.home() / 'AppData' / 'Local' / 'Steam')

    seen_steam = set()
    expanded_libraries = []
    for steam_root in steam_roots:
        if str(steam_root).lower() in seen_steam:
            continue
        seen_steam.add(str(steam_root).lower())
        expanded_libraries.append(steam_root)
        vdf = steam_root / 'steamapps' / 'libraryfolders.vdf'
        try:
            if vdf.is_file():
                for value in parse_steam_libraryfolders(vdf.read_text(encoding='utf-8', errors='ignore')):
                    expanded_libraries.append(Path(value))
        except OSError:
            pass

    game_names = ('ForzaHorizon6', 'Forza Horizon 6')
    for library in expanded_libraries:
        for name in game_names:
            candidates.append(library / 'steamapps' / 'common' / name)

    for letter in 'CDEFGH':
        drive = Path(f'{letter}:\\')
        for name in game_names:
            candidates.append(drive / 'XboxGames' / name)
            candidates.append(drive / 'XboxGames' / name / 'Content')
    return candidates


def discover_game_roots(candidates=None):
    """Filter candidate locations down to plausible FH6 content roots."""
    candidates = list(candidates) if candidates is not None else _default_install_candidates()
    roots = []
    seen = set()
    for candidate in candidates:
        path = Path(candidate).expanduser()
        normalized = None
        if looks_like_fh6_root(path):
            normalized = path
            content = path / 'Content'
            if content.is_dir() and looks_like_fh6_root(content):
                normalized = content
        elif (path / 'Content').is_dir() and looks_like_fh6_root(path / 'Content'):
            normalized = path / 'Content'
        if normalized is None:
            continue
        try:
            resolved = normalized.resolve()
        except OSError:
            resolved = normalized.absolute()
        key = str(resolved).lower()
        if key not in seen:
            seen.add(key)
            roots.append(resolved)
    return roots


def create_report_bundle(paths, output_dir):
    output_dir = Path(output_dir)
    bundle = output_dir / 'FH6_Game_Nav_Probe_Report.zip'
    with zipfile.ZipFile(bundle, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for path in paths:
            path = Path(path)
            zf.write(path, arcname=path.name)
    return bundle


def _select_game_root(explicit=None):
    if explicit:
        path = Path(explicit).expanduser()
        if not looks_like_fh6_root(path):
            raise ValueError(f'Folder does not look like an FH6 install: {path}')
        content = path / 'Content'
        if content.is_dir() and looks_like_fh6_root(content):
            return content.resolve()
        return path.resolve()

    roots = discover_game_roots()
    if len(roots) == 1:
        return roots[0]
    if len(roots) > 1:
        print('Found possible FH6 installations:')
        for idx, root in enumerate(roots, 1):
            print(f'  {idx}. {root}')
        try:
            raw = input(f'Select 1-{len(roots)} [1]: ').strip()
        except EOFError:
            raw = ''
        choice = 1 if not raw else int(raw)
        if choice < 1 or choice > len(roots):
            raise ValueError('Invalid installation selection')
        return roots[choice - 1]

    try:
        raw = input('FH6 was not found automatically. Paste the game folder path: ').strip().strip('"')
    except EOFError:
        raw = ''
    if not raw:
        raise ValueError('FH6 folder was not provided')
    return _select_game_root(raw)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Read-only FH6 navigation asset probe')
    parser.add_argument('game_folder', nargs='?', help='FH6 install/content folder. You can drag the folder onto the BAT file.')
    parser.add_argument('--output', default=str(Path(__file__).with_name('probe_output')), help='Directory for shareable reports')
    parser.add_argument('--deep', action='store_true', help='Scan larger binary packages (slower)')
    args = parser.parse_args(argv)

    try:
        game_root = _select_game_root(args.game_folder)
    except (ValueError, OSError) as exc:
        print(f'ERROR: {exc}')
        return 2

    output_dir = Path(args.output).expanduser().resolve()
    print('FH6 Game Nav Asset Probe')
    print('------------------------')
    print(f'Game: {game_root}')
    print('Mode: read-only; no game files will be modified.')
    print('Scanning... this can take several minutes on a large installation.')

    try:
        if args.deep:
            report = scan_game_root(
                game_root,
                sample_bytes=2 * 1024 * 1024,
                max_binary_file=1024 * 1024 * 1024,
                binary_scan_budget=2 * 1024 * 1024 * 1024,
            )
        else:
            report = scan_game_root(game_root)
        report['probe_mode'] = 'deep' if args.deep else 'standard'
        paths = write_reports(report, output_dir)
        bundle = create_report_bundle(paths, output_dir)
    except Exception as exc:
        print(f'ERROR while scanning: {exc}')
        return 3

    stats = report['stats']
    print('')
    print(f"Scanned files: {stats['scanned_files']}")
    print(f"Candidates: {stats['candidate_files']}")
    print(f"Unreadable files: {stats['unreadable_files']}")
    print('')
    print('DONE. Send this file back to ChatGPT:')
    print(bundle)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
