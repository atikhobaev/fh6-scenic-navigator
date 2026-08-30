"""Focused read-only reverse-engineering probe for FH6 .nav assets.

It selects a small representative set of NAV files, performs conservative
binary analysis, and packages the reports plus the selected original NAV
samples. The game directory is never modified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import struct
import zipfile
from collections import Counter
from pathlib import Path

from game_nav_probe import _select_game_root, extract_strings

REPORT_FORMAT = 'fh6-nav-binary-probe-v1'
DEFAULT_ROUTE_COUNT = 4
HEADER_BYTES = 256
TAIL_BYTES = 256
MAX_STRING_COUNT = 64


def _all_nav_files(root: Path):
    root = Path(root)
    freeroam = root / 'media' / 'OpenWorld' / 'Brio' / 'Freeroam' / 'Brio_00.nav'
    if not freeroam.is_file():
        # Case-insensitive fallback for unusual installations.
        matches = [p for p in root.rglob('*.nav') if p.name.lower() == 'brio_00.nav']
        freeroam = matches[0] if matches else None
    routes = sorted(
        (p for p in root.rglob('*.nav') if p.name.lower().startswith('route')),
        key=lambda p: (p.stat().st_size, p.as_posix().lower()),
    )
    return freeroam, routes


def _quantile_indices(n: int, count: int):
    if n <= 0 or count <= 0:
        return []
    if count >= n:
        return list(range(n))
    if count == 1:
        return [n // 2]
    raw = [round(i * (n - 1) / (count - 1)) for i in range(count)]
    result = []
    for idx in raw:
        if idx not in result:
            result.append(idx)
    # Rounding can collapse adjacent quantiles for small sets.
    if len(result) < count:
        for idx in range(n):
            if idx not in result:
                result.append(idx)
            if len(result) == count:
                break
    return sorted(result[:count])


def select_nav_samples(root, route_count: int = DEFAULT_ROUTE_COUNT):
    """Return Brio_00.nav followed by Route*.nav samples spanning file sizes."""
    root = Path(root).expanduser().resolve()
    freeroam, routes = _all_nav_files(root)
    if freeroam is None or not freeroam.is_file():
        raise ValueError('Brio_00.nav was not found under media/OpenWorld/Brio/Freeroam')
    if not routes:
        raise ValueError('No Route*.nav files were found under the FH6 installation')
    route_count = max(1, min(int(route_count), len(routes)))
    selected_routes = [routes[i] for i in _quantile_indices(len(routes), route_count)]
    return [freeroam, *selected_routes]


def hexdump(data: bytes, *, limit: int = 256, start_offset: int = 0) -> str:
    data = bytes(data[:max(0, int(limit))])
    lines = []
    for base in range(0, len(data), 16):
        chunk = data[base:base + 16]
        hex_part = ' '.join(f'{b:02x}' for b in chunk)
        ascii_part = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
        lines.append(f'{start_offset + base:08x}  {hex_part:<47}  |{ascii_part}|')
    return '\n'.join(lines)


def shannon_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    total = len(data)
    value = -sum((count / total) * math.log2(count / total) for count in counts.values())
    return round(value, 6)


def float32_summary(data: bytes) -> dict:
    total = len(data) // 4
    finite = 0
    nonfinite = 0
    moderate = 0
    tiny = 0
    very_large = 0
    samples = []
    for offset in range(0, total * 4, 4):
        value = struct.unpack_from('<f', data, offset)[0]
        if not math.isfinite(value):
            nonfinite += 1
            continue
        finite += 1
        av = abs(value)
        if av <= 100000:
            moderate += 1
            if value != 0 and len(samples) < 24:
                samples.append({'offset': offset, 'value': round(value, 6)})
        if 0 < av < 1e-20:
            tiny += 1
        if av > 1e12:
            very_large += 1
    return {
        'total_aligned_values': total,
        'finite_values': finite,
        'nonfinite_values': nonfinite,
        'moderate_abs_le_100000': moderate,
        'tiny_nonzero_abs_lt_1e-20': tiny,
        'very_large_abs_gt_1e12': very_large,
        'moderate_samples': samples,
    }


def candidate_record_strides(
    file_size: int,
    *,
    offsets=(0, 4, 8, 12, 16, 20, 24, 32, 48, 64, 96, 128, 256),
    strides=(8, 12, 16, 20, 24, 28, 32, 36, 40, 48, 56, 64, 72, 80, 96, 112, 128),
):
    """Weak structural hint: payload lengths that divide cleanly into records."""
    result = []
    for offset in offsets:
        payload = int(file_size) - int(offset)
        if payload <= 0:
            continue
        for stride in strides:
            records, remainder = divmod(payload, stride)
            if records >= 4 and remainder == 0:
                result.append({'offset': int(offset), 'stride': int(stride), 'records': records})
    return result


def repeated_block_summary(data: bytes, *, block_sizes=(4, 8, 16, 32), top_n=8) -> dict:
    result = {}
    for block_size in block_sizes:
        counter = Counter(
            data[i:i + block_size]
            for i in range(0, len(data) - block_size + 1, block_size)
        )
        repeated = []
        for block, count in counter.most_common(top_n * 3):
            if count <= 1:
                break
            repeated.append({'hex': block.hex(), 'count': count})
            if len(repeated) >= top_n:
                break
        result[str(block_size)] = repeated
    return result


def _interesting_strings(data: bytes) -> list[str]:
    strings = extract_strings(data, min_len=5)
    result = []
    for value in strings:
        cleaned = value.strip().replace('\x00', '')
        if not cleaned or cleaned in result:
            continue
        result.append(cleaned[:320])
        if len(result) >= MAX_STRING_COUNT:
            break
    return result


def analyze_nav_file(path) -> dict:
    path = Path(path)
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    header = data[:HEADER_BYTES]
    tail = data[-TAIL_BYTES:] if data else b''
    tail_offset = max(0, len(data) - len(tail))
    return {
        'size_bytes': len(data),
        'sha256': digest,
        'entropy_bits_per_byte': shannon_entropy(data),
        'header_hexdump': hexdump(header, limit=HEADER_BYTES, start_offset=0),
        'tail_hexdump': hexdump(tail, limit=TAIL_BYTES, start_offset=tail_offset),
        'strings': _interesting_strings(data),
        'float32': float32_summary(data),
        'record_stride_candidates': candidate_record_strides(len(data)),
        'repeated_blocks': repeated_block_summary(data),
    }


def _common_prefix_length(a: bytes, b: bytes, *, cap=4096) -> int:
    limit = min(len(a), len(b), cap)
    for i in range(limit):
        if a[i] != b[i]:
            return i
    return limit


def _sample_comparison(selected: list[Path]) -> dict:
    headers = {p.name: p.read_bytes()[:4096] for p in selected}
    pairs = []
    names = list(headers)
    for i, left in enumerate(names):
        for right in names[i + 1:]:
            pairs.append({
                'left': left,
                'right': right,
                'common_prefix_bytes_up_to_4096': _common_prefix_length(headers[left], headers[right]),
            })
    return {'header_pair_comparisons': pairs}


def _write_report_files(report: dict, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / 'nav_binary_report.json'
    txt_path = output_dir / 'nav_binary_report.txt'
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

    lines = [
        'FH6 NAV BINARY PROBE',
        '====================',
        f"Game root: {report.get('game_root_name', 'unknown')}",
        f"Samples: {len(report.get('samples', []))}",
        '',
    ]
    for idx, sample in enumerate(report.get('samples', []), 1):
        a = sample['analysis']
        lines.extend([
            f"{idx}. {sample['relative_path']}",
            f"   size: {a['size_bytes']} bytes",
            f"   sha256: {a['sha256']}",
            f"   entropy: {a['entropy_bits_per_byte']:.4f} bits/byte",
            f"   strings: {len(a['strings'])}",
            f"   stride candidates: {len(a['record_stride_candidates'])}",
            '   HEADER:',
            *('      ' + line for line in a['header_hexdump'].splitlines()),
            '   TAIL:',
            *('      ' + line for line in a['tail_hexdump'].splitlines()),
            '',
        ])
    lines.append('HEADER COMPARISONS')
    lines.append('------------------')
    for item in report.get('comparison', {}).get('header_pair_comparisons', []):
        lines.append(
            f"{item['left']} vs {item['right']}: common prefix {item['common_prefix_bytes_up_to_4096']} bytes"
        )
    txt_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return [json_path, txt_path]


def build_nav_probe_bundle(root, output_dir, *, route_count: int = DEFAULT_ROUTE_COUNT):
    root = Path(root).expanduser().resolve()
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    selected = select_nav_samples(root, route_count=route_count)

    samples = []
    for path in selected:
        samples.append({
            'relative_path': path.relative_to(root).as_posix(),
            'analysis': analyze_nav_file(path),
        })
    report = {
        'format': REPORT_FORMAT,
        'game_root_name': root.name,
        'samples': samples,
        'comparison': _sample_comparison(selected),
    }
    report_paths = _write_report_files(report, output_dir)
    bundle = output_dir / 'FH6_NAV_Binary_Probe.zip'
    with zipfile.ZipFile(bundle, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for report_path in report_paths:
            zf.write(report_path, arcname=report_path.name)
        for path in selected:
            rel = path.relative_to(root).as_posix()
            zf.write(path, arcname=f'samples/{rel}')
    return bundle


def main(argv=None):
    parser = argparse.ArgumentParser(description='Read-only FH6 .nav binary format probe')
    parser.add_argument('game_folder', nargs='?', help='FH6 install/content folder. You can drag it onto the BAT file.')
    parser.add_argument('--output', default=str(Path(__file__).with_name('nav_probe_output')))
    parser.add_argument('--route-count', type=int, default=DEFAULT_ROUTE_COUNT)
    args = parser.parse_args(argv)

    try:
        game_root = _select_game_root(args.game_folder)
        selected = select_nav_samples(game_root, route_count=args.route_count)
    except (ValueError, OSError) as exc:
        print(f'ERROR: {exc}')
        return 2

    print('FH6 NAV Binary Probe')
    print('--------------------')
    print(f'Game: {game_root}')
    print('Read-only mode. Game files will not be changed.')
    print('Selected samples:')
    for path in selected:
        print(f'  {path.relative_to(game_root)}  ({path.stat().st_size} bytes)')
    print('Analyzing and packaging selected NAV files...')

    try:
        bundle = build_nav_probe_bundle(game_root, args.output, route_count=args.route_count)
    except Exception as exc:
        print(f'ERROR while probing NAV files: {exc}')
        return 3

    print('')
    print('DONE. Send this ZIP back to ChatGPT:')
    print(bundle)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
