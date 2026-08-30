#!/usr/bin/env python3
"""Safe Windows launcher for FH6 Scenic Navigator.

Normal startup is intentionally offline for Planner catalog data: it validates
only files bundled with the release, then starts the local server. No third-
party place/image catalog is downloaded here.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.request

HTTP_PORT = 8080
NAVIGATOR_NAME = 'FH6 Scenic Navigator'


def probe_existing_navigator(port: int = HTTP_PORT, timeout: float = 0.4) -> dict | None:
    """Probe localhost only, to avoid opening a stale Navigator build."""
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/info', timeout=timeout) as response:
            payload = json.loads(response.read().decode('utf-8'))
            return payload if isinstance(payload, dict) else None
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, json.JSONDecodeError):
        return None


def is_fh6_navigator(info: dict | None) -> bool:
    return bool(info and info.get('name') == NAVIGATOR_NAME)


def listener_pid_from_netstat(text: str, port: int = HTTP_PORT) -> int | None:
    wanted = str(port)
    for raw in text.splitlines():
        parts = raw.split()
        if len(parts) < 5 or parts[0].upper() != 'TCP':
            continue
        local, state, pid_text = parts[1], parts[-2], parts[-1]
        if not state.upper().startswith('LISTEN'):
            continue
        if local.rsplit(':', 1)[-1] != wanted:
            continue
        try:
            return int(pid_text)
        except ValueError:
            continue
    return None


def _port_in_use(port: int = HTTP_PORT) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(('127.0.0.1', port)) == 0


def _windows_listener_pid(port: int = HTTP_PORT) -> int | None:
    completed = subprocess.run(
        ['netstat', '-ano', '-p', 'tcp'],
        capture_output=True,
        text=True,
        errors='replace',
        check=False,
    )
    return listener_pid_from_netstat(completed.stdout, port)


def _wait_port_free(port: int = HTTP_PORT, timeout: float = 4.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _port_in_use(port):
            return True
        time.sleep(0.1)
    return not _port_in_use(port)


def stop_previous_navigator(port: int = HTTP_PORT) -> bool:
    """Stop a previous FH6 Navigator on the default port, never an unknown app."""
    if not _port_in_use(port):
        return False
    info = probe_existing_navigator(port)
    if not is_fh6_navigator(info):
        raise RuntimeError(
            f'HTTP port {port} is already used by another application. '
            'Close that application or free the port before starting FH6 Navigator.'
        )
    previous = info.get('version') or 'older build'
    if os.name != 'nt':
        raise RuntimeError(
            f'Another FH6 Navigator ({previous}) is already running on port {port}. '
            'Stop it before starting this build.'
        )
    pid = _windows_listener_pid(port)
    if not pid or pid == os.getpid():
        raise RuntimeError(
            f'Found FH6 Navigator ({previous}) on port {port}, but could not identify its Windows process. '
            'Close the old Navigator console and run start.bat again.'
        )
    print(f'      stopping previous FH6 Navigator ({previous}), PID {pid}...', flush=True)
    os.kill(pid, signal.SIGTERM)
    if not _wait_port_free(port):
        raise RuntimeError(f'The previous FH6 Navigator did not release port {port}. Close it manually and retry.')
    return True


def inspect_bundled_catalog(*, root: Path | None = None) -> dict:
    """Validate release-owned Planner data without contacting the internet."""
    root = Path(root) if root is not None else Path(__file__).resolve().parent
    data_dir = root / 'static' / 'data'
    catalog_path = data_dir / 'builtin_places.json'
    graph_path = data_dir / 'fh6_navgraph_v1.json.gz'
    roads_path = data_dir / 'fh6_roads.json'

    if not catalog_path.is_file():
        raise RuntimeError(f'bundled map catalog is missing: {catalog_path}')
    try:
        doc = json.loads(catalog_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f'bundled map catalog is unreadable: {exc}') from exc
    if doc.get('schema_version') != 1 or not isinstance(doc.get('places'), list):
        raise RuntimeError('bundled map catalog has an unsupported or malformed schema')

    places = doc['places']
    if not places:
        raise RuntimeError('bundled map catalog contains no places')
    build = doc.get('build') or {}
    runtime_places = int(build.get('runtime_places') or len(places))
    if runtime_places != len(places):
        raise RuntimeError(
            f'bundled map catalog metadata mismatch: build says {runtime_places} places, file contains {len(places)}'
        )

    reported = int(build.get('reported_source_markers') or runtime_places)
    captured = int(build.get('coordinate_records_captured') or runtime_places)
    reason = str(build.get('coverage_limited_reason') or '').strip()
    coverage_limited = reported > runtime_places
    if coverage_limited and not reason:
        raise RuntimeError('bundled map catalog is coverage-limited but does not explain the limitation')
    if captured < runtime_places:
        raise RuntimeError(
            f'bundled map catalog metadata mismatch: only {captured} captured coordinate records for {runtime_places} places'
        )

    if not graph_path.is_file() or graph_path.stat().st_size <= 0:
        raise RuntimeError(f'bundled Directed WVAN graph is missing: {graph_path}')
    if not roads_path.is_file() or roads_path.stat().st_size <= 0:
        raise RuntimeError(f'bundled FH6 road dataset is missing: {roads_path}')
    try:
        roads_doc = json.loads(roads_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f'bundled FH6 road dataset is unreadable: {exc}') from exc
    roads = roads_doc.get('roads') if isinstance(roads_doc, dict) else None
    if not isinstance(roads, list) or not roads:
        raise RuntimeError('bundled FH6 road dataset is malformed or empty')

    return {
        'status': 'ready',
        'runtime_places': runtime_places,
        'reported_source_markers': reported,
        'coordinate_records_captured': captured,
        'coverage_limited': coverage_limited,
        'coverage_limited_reason': reason if coverage_limited else '',
        'graph_bytes': graph_path.stat().st_size,
        'road_count': len(roads),
    }



def refresh_game_localization_cache(*, root: Path | None = None) -> dict:
    """Refresh Navigator-owned POI name cache from installed FH6 StringTables.

    Game files are read-only inputs. If StringTables cannot be found, the existing
    cache is left untouched and runtime uses its English fallback names. A small
    Navigator-owned metadata file is always refreshed so the UI can report whether
    official localized POI names are actually available.
    """
    root = Path(root) if root is not None else Path(__file__).resolve().parent
    from game_localization import find_stringtables_dir, refresh_place_names, localization_coverage

    data_dir=root/'static'/'data'
    target=data_dir/'place_names.json'
    meta_target=data_dir/'place_names_meta.json'
    try:
        builtin=json.loads((data_dir/'builtin_places.json').read_text(encoding='utf-8'))
        places=builtin if isinstance(builtin,list) else builtin.get('places') or []
        total_game_places=sum(1 for place in places if place.get('source')=='game')
    except (OSError,json.JSONDecodeError):
        total_game_places=0

    tables = find_stringtables_dir()
    if tables is None:
        try:
            existing = json.loads(target.read_text(encoding='utf-8')) if target.is_file() else {}
        except (OSError, json.JSONDecodeError):
            existing = {}
        result={
            'status':'fallback',
            'localized_places':len(existing) if isinstance(existing,dict) else 0,
            'total_game_places':total_game_places,
            'coverage':localization_coverage(existing if isinstance(existing,dict) else {},total_game_places),
        }
    else:
        names = refresh_place_names(root / 'static', tables)
        result={
            'status':'ready',
            'localized_places':len(names),
            'total_game_places':total_game_places,
            'coverage':localization_coverage(names,total_game_places),
            'stringtables_dir':str(tables),
        }
    data_dir.mkdir(parents=True,exist_ok=True)
    tmp=meta_target.with_suffix('.tmp')
    tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    os.replace(tmp,meta_target)
    return result



def server_args_from_env(env: dict[str, str] | None = None) -> list[str]:
    env = dict(os.environ if env is None else env)
    http_port = str(int(env.get('FH6_HTTP_PORT', HTTP_PORT)))
    udp_port = str(int(env.get('FH6_UDP_PORT', 1234)))
    args = ['--http-port', http_port, '--udp-port', udp_port]
    if env.get('FH6_NATIVE_LAUNCHER') != '1':
        args.append('--open-browser')
    return args

def main() -> int:
    env = dict(os.environ)
    http_port = int(env.get('FH6_HTTP_PORT', HTTP_PORT))
    print(f'[1/4] Checking local port {http_port} and previous Navigator...', flush=True)
    try:
        stopped = stop_previous_navigator(http_port)
    except RuntimeError as exc:
        print('')
        print(f'ERROR: {exc}', flush=True)
        print('')
        return 2
    print('      OK: previous Navigator stopped.' if stopped else f'      OK: port {http_port} is available.', flush=True)

    print('[2/4] Validating bundled OFFLINE map data...', flush=True)
    try:
        catalog = inspect_bundled_catalog()
    except RuntimeError as exc:
        print('')
        print(f'ERROR: {exc}', flush=True)
        print('Re-extract the release ZIP if a bundled graph/road file is missing; update_map_data.bat rebuilds local catalog JSON.', flush=True)
        print('')
        return 2
    print(
        f"      OK: {catalog['runtime_places']} verified bundled game POIs + {catalog['road_count']} road records + Directed WVAN graph.",
        flush=True,
    )
    if catalog['coverage_limited']:
        print(
            f"      INFO: public source index reports {catalog['reported_source_markers']} markers; "
            f"this release embeds {catalog['coordinate_records_captured']} reviewed coordinate records.",
            flush=True,
        )
    print('      Internet catalog download: DISABLED.', flush=True)

    print('[3/4] Loading official FH6 localization cache...', flush=True)
    localization = refresh_game_localization_cache()
    labels={'en-US':'EN','zh-CN':'ZH','ru-RU':'RU','es-419':'ES-LATAM'}
    coverage=' | '.join(f"{labels[loc]} {row['matched']}/{row['total']}" for loc,row in localization.get('coverage',{}).items())
    if localization['status'] == 'ready':
        print(f"      OK: official StringTables found: {localization.get('stringtables_dir','')}", flush=True)
        print(f"      POI localization: {coverage}", flush=True)
    else:
        print('      INFO: FH6 StringTables not found; English game names remain the safe fallback.', flush=True)
        if coverage: print(f"      POI localization cache: {coverage}", flush=True)

    # Import only after local preflight so no Planner DB/graph work is done for a stale instance.
    print('[4/4] Starting local Navigator server and browser...', flush=True)
    import server
    return server.main(server_args_from_env(env))


if __name__ == '__main__':
    raise SystemExit(main())
