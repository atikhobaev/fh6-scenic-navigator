#!/usr/bin/env python3
"""FH6 Scenic Navigator: zero-dependency LAN telemetry/map server."""
from __future__ import annotations

import argparse
import gzip
import json
import os
from pathlib import Path
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from telemetry import parse_packet

ROOT = Path(__file__).resolve().parent
USER_DATA_ROOT = Path(os.environ.get('FH6_USER_DATA_DIR', ROOT)).resolve()
STATIC_DIR = ROOT / 'static'
CACHE_DIR = USER_DATA_ROOT / 'cache' / 'maptiles'
MAPGENIE_BASE = 'https://tiles.mapgenie.io/games/forza-horizon-6/one/default-v2'
DEFAULT_UDP_PORT = 1234
APP_VERSION = '1.20.0'
SERVER_PROGRESS_STEPS = ('[server 1/3]', '[server 2/3]', '[server 3/3]')
ROAD_DATA_FILE = STATIC_DIR / 'data' / 'fh6_roads.json'
ROAD_CACHE_FILE = ROAD_DATA_FILE  # compatibility alias; runtime data is bundled, not downloaded
ROAD_GRAPH_GITHUB_URL = 'https://raw.githubusercontent.com/Elgeryy1/forza-drive/refs/heads/main/app/src/main/assets/fh6_labsgg_roads.json'
FORZALABS_MAP_URL = 'https://forza.labsgg.com/interactive-map'
NAVGRAPH_FILE = STATIC_DIR / 'data' / 'fh6_navgraph_v1.json.gz'


def extract_js_value(html: str, name: str) -> str:
    marker = f'const {name} = '
    start = html.index(marker) + len(marker)
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(html)):
        ch = html[i]
        if in_string:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch in '[{':
            depth += 1
        elif ch in ']}':
            depth -= 1
        elif ch == ';' and depth == 0:
            return html[start:i]
    raise ValueError(f'Could not parse {name}')


def _http_get_bytes(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 FH6-Scenic-Navigator/1.7',
            'Accept': 'application/json,text/html,*/*;q=0.8',
        },
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return response.read()


def _valid_road_dataset(data: object) -> bool:
    if not isinstance(data, dict):
        return False
    roads = data.get('roads')
    if not isinstance(roads, list) or not roads:
        return False
    return any(isinstance(r, dict) and isinstance(r.get('points'), list) and len(r['points']) >= 2 for r in roads)


class RoadNetworkProvider:
    def __init__(self, cache_file: Path = ROAD_DATA_FILE, fetch_bytes=None, allow_download: bool = False):
        self.cache_file = Path(cache_file).resolve()
        self.fetch_bytes = fetch_bytes or _http_get_bytes
        self.allow_download = bool(allow_download)
        self._lock = threading.Lock()
        self._memory = None

    def get(self) -> dict:
        with self._lock:
            if self._memory is not None:
                return self._memory
            if self.cache_file.exists():
                try:
                    cached = json.loads(self.cache_file.read_text(encoding='utf-8'))
                    if _valid_road_dataset(cached):
                        self._memory = cached
                        return cached
                except (OSError, json.JSONDecodeError):
                    pass

            if not self.allow_download:
                raise OSError(f'bundled FH6 road dataset is missing or invalid: {self.cache_file}')
            data = self._download()
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.cache_file.with_suffix('.tmp')
            tmp.write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
            os.replace(tmp, self.cache_file)
            self._memory = data
            return data

    def _download(self) -> dict:
        errors = []
        try:
            data = json.loads(self.fetch_bytes(ROAD_GRAPH_GITHUB_URL).decode('utf-8'))
            if _valid_road_dataset(data):
                return {'source': data.get('source', ROAD_GRAPH_GITHUB_URL), 'roads': data['roads']}
            errors.append('GitHub road dataset was invalid')
        except Exception as exc:  # network/data fallback path
            errors.append(f'GitHub: {exc}')

        try:
            html = self.fetch_bytes(FORZALABS_MAP_URL).decode('utf-8', errors='replace')
            roads = json.loads(extract_js_value(html, 'roads'))
            data = {'source': FORZALABS_MAP_URL, 'roads': roads}
            if _valid_road_dataset(data):
                return data
            errors.append('ForzaLabs road dataset was invalid')
        except Exception as exc:  # network/data fallback path
            errors.append(f'ForzaLabs: {exc}')
        raise OSError('Could not load FH6 road graph: ' + ' | '.join(errors))


class NavGraphProvider:
    def __init__(self, path: Path = NAVGRAPH_FILE):
        self.path = Path(path)
        self._lock = threading.Lock()
        self._raw = None
        self._info = None

    def get_gzip(self) -> bytes:
        with self._lock:
            if self._raw is None:
                if not self.path.is_file():
                    raise OSError(f'Directed WVAN graph not found: {self.path}')
                self._raw = self.path.read_bytes()
            return self._raw

    def info(self) -> dict:
        with self._lock:
            if self._info is not None:
                return dict(self._info)
            if not self.path.is_file():
                self._info = {'available': False, 'format': None, 'capabilities': {}}
                return dict(self._info)
            try:
                payload = json.loads(gzip.decompress(self.path.read_bytes()).decode('utf-8'))
                self._info = {
                    'available': payload.get('format') == 'fh6-navgraph-v1',
                    'format': payload.get('format'),
                    'capabilities': payload.get('capabilities') or {},
                    'source': payload.get('source') or {},
                    'stats': payload.get('stats') or {},
                }
            except Exception as exc:
                self._info = {'available': False, 'format': None, 'capabilities': {}, 'error': str(exc)}
            return dict(self._info)


class TelemetryState:
    def __init__(self, timeout_s: float = 2.5):
        self.timeout_s = timeout_s
        self._lock = threading.Lock()
        self._packet = None
        self._source_ip = None
        self._updated_monotonic = None

    def update(self, packet: dict, source_ip: str) -> None:
        with self._lock:
            self._packet = dict(packet)
            self._source_ip = source_ip
            self._updated_monotonic = time.monotonic()

    def snapshot(self) -> dict:
        with self._lock:
            packet = dict(self._packet) if self._packet is not None else None
            source_ip = self._source_ip
            updated = self._updated_monotonic
        if updated is None:
            return {'connected': False, 'ageMs': None, 'sourceIp': source_ip, 'packet': packet}
        age_ms = max(0, int((time.monotonic() - updated) * 1000))
        return {
            'connected': age_ms < int(self.timeout_s * 1000),
            'ageMs': age_ms,
            'sourceIp': source_ip,
            'packet': packet,
        }


def tile_upstream_url(z: int, x: int, y: int) -> str:
    # MapGenie FH6 uses z/y/x in the public tile URL.
    return f'{MAPGENIE_BASE}/{z}/{y}/{x}.jpg'


def discover_lan_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(('8.8.8.8', 80))
        return sock.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return '127.0.0.1'
    finally:
        sock.close()


def create_udp_socket(bind_ip: str, udp_port: int) -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((bind_ip, udp_port))
    except Exception:
        sock.close()
        raise
    sock.settimeout(0.5)
    return sock


def udp_receiver(state: TelemetryState, sock: socket.socket, stop: threading.Event) -> None:
    bind_ip, udp_port = sock.getsockname()[:2]
    print(f'[UDP] listening on {bind_ip}:{udp_port}')
    try:
        while not stop.is_set():
            try:
                data, addr = sock.recvfrom(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            packet = parse_packet(data)
            if packet is not None:
                state.update(packet, addr[0])
    finally:
        sock.close()


class NavigatorHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        exc = sys.exc_info()[1]
        if isinstance(exc, (BrokenPipeError, ConnectionResetError, ConnectionAbortedError)):
            return
        super().handle_error(request, client_address)


class NavigatorHandler(SimpleHTTPRequestHandler):
    state: TelemetryState = None  # type: ignore[assignment]
    road_provider = RoadNetworkProvider()
    navgraph_provider = NavGraphProvider()
    lan_ip: str = '127.0.0.1'
    udp_port: int = DEFAULT_UDP_PORT
    planner_api = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def log_message(self, fmt, *args):
        # Keep console useful: suppress repetitive telemetry polling.
        if self.path.startswith('/api/telemetry'):
            return
        super().log_message(fmt, *args)

    def end_headers(self):
        path = urlparse(self.path).path
        if path == '/' or path.endswith('/') or path.endswith(('.html', '.js', '.css')):
            self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def _json(self, payload: dict, status: int = 200):
        body = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _planner_dispatch(self, method):
        parsed = urlparse(self.path)
        api = getattr(self, 'planner_api', None)
        if api is not None and api.handle(self, method, parsed.path):
            return True
        return False

    def do_POST(self):
        if self._planner_dispatch('POST'): return
        self.send_error(404)

    def do_PUT(self):
        if self._planner_dispatch('PUT'): return
        self.send_error(404)

    def do_PATCH(self):
        if self._planner_dispatch('PATCH'): return
        self.send_error(404)

    def do_DELETE(self):
        if self._planner_dispatch('DELETE'): return
        self.send_error(404)

    def do_GET(self):
        parsed = urlparse(self.path)
        if self._planner_dispatch('GET'): return
        if parsed.path == '/favicon.ico':
            self.send_response(204)
            self.send_header('Cache-Control', 'public, max-age=86400')
            self.end_headers()
            return
        if parsed.path == '/api/telemetry':
            self._json(self.state.snapshot())
            return
        if parsed.path == '/api/info':
            self._json({
                'name': 'FH6 Scenic Navigator',
                'version': APP_VERSION,
                'lanIp': self.lan_ip,
                'httpPort': self.server.server_port,
                'udpPort': self.udp_port,
                'navGraph': self.navgraph_provider.info(),
            })
            return
        if parsed.path == '/api/roads':
            try:
                self._json(self.road_provider.get())
            except OSError as exc:
                self._json({'error': str(exc), 'roads': []}, status=502)
            return
        if parsed.path == '/api/navgraph':
            try:
                body = self.navgraph_provider.get_gzip()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Encoding', 'gzip')
                self.send_header('Cache-Control', 'public, max-age=3600')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except OSError as exc:
                self._json({'error': str(exc), 'format': None}, status=503)
            return
        if parsed.path.startswith('/maptile/'):
            self._serve_tile(parsed.path)
            return
        return super().do_GET()

    def _serve_tile(self, path: str):
        # Expected /maptile/{z}/{x}/{y}.jpg
        parts = path.strip('/').split('/')
        try:
            if len(parts) != 4 or parts[0] != 'maptile':
                raise ValueError
            z = int(parts[1]); x = int(parts[2]); y = int(parts[3].removesuffix('.jpg'))
            if not (11 <= z <= 14 and 0 <= x < 2**z and 0 <= y < 2**z):
                raise ValueError
        except ValueError:
            self.send_error(400, 'Bad tile coordinates')
            return

        local = CACHE_DIR / str(z) / str(x) / f'{y}.jpg'
        if not local.exists():
            local.parent.mkdir(parents=True, exist_ok=True)
            req = urllib.request.Request(
                tile_upstream_url(z, x, y),
                headers={
                    'User-Agent': 'Mozilla/5.0 FH6-Scenic-Navigator/1.0',
                    'Referer': 'https://mapgenie.io/',
                    'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = response.read()
                    ctype = response.headers.get('Content-Type', '')
                if len(data) < 500 or 'image' not in ctype.lower():
                    raise OSError('upstream did not return an image')
                tmp = local.with_suffix('.tmp')
                tmp.write_bytes(data)
                os.replace(tmp, local)
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
                self.send_error(502, f'Map tile unavailable: {exc}')
                return

        data = local.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', 'image/jpeg')
        self.send_header('Cache-Control', 'public, max-age=2592000')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)



def create_default_planner_api(db_path: Path | None = None):
    from planner_database import PlannerDatabase
    from route_service import RouteService
    from planner_events import PlannerEventBus
    from planner_api import PlannerAPI
    from places_service import PlacesService
    db = PlannerDatabase(db_path or (USER_DATA_ROOT / 'data' / 'navigator.db'))
    db.initialize()
    events = PlannerEventBus()
    places = PlacesService(
        STATIC_DIR / 'data' / 'builtin_places.json',
        STATIC_DIR / 'data' / 'scenic_catalog.json',
        db,
        NAVGRAPH_FILE,
        community_path=STATIC_DIR / 'data' / 'community_places.json',
        media_root=STATIC_DIR / 'media' / 'places',
    )
    from route_preview import DirectedGraph, RoutePreviewService
    from navigation_service import NavigationService
    from builtin_routes import BuiltinRouteProvider
    from planner_io import PlannerIO
    from catalog_validator import runtime_diagnostics
    preview = RoutePreviewService(DirectedGraph.from_gzip_path(NAVGRAPH_FILE), places)
    builtins = BuiltinRouteProvider(
        STATIC_DIR / 'route.json',
        STATIC_DIR / 'data' / 'scenic_catalog.json',
    )
    routes = RouteService(db, preview_service=preview, builtin_routes=builtins)
    navigation = NavigationService(db, routes, preview)
    io = PlannerIO(db, routes, places)
    return PlannerAPI(routes, events, places, navigation, io_service=io, diagnostics_provider=lambda: runtime_diagnostics(places,NAVGRAPH_FILE))

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='FH6 Scenic Navigator')
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--http-port', type=int, default=8080)
    parser.add_argument('--udp-port', type=int, default=DEFAULT_UDP_PORT)
    parser.add_argument('--open-browser', action='store_true')
    args = parser.parse_args(argv)

    state = TelemetryState()
    stop = threading.Event()
    lan_ip = discover_lan_ip()

    NavigatorHandler.state = state
    NavigatorHandler.lan_ip = lan_ip
    NavigatorHandler.udp_port = args.udp_port
    print(f'{SERVER_PROGRESS_STEPS[0]} Loading Planner database and bundled Directed WVAN graph...', flush=True)
    NavigatorHandler.planner_api = create_default_planner_api()
    print('      OK: Planner data and directed routing graph loaded.', flush=True)

    print(f'{SERVER_PROGRESS_STEPS[1]} Binding Forza UDP socket on port {args.udp_port}...', flush=True)
    try:
        udp_sock = create_udp_socket(args.host, args.udp_port)
    except OSError as exc:
        print(f'ERROR: Forza UDP port {args.udp_port} is unavailable: {exc}')
        print('Close the previous FH6 Navigator instance and run start.bat again.')
        return 2
    print('      OK: Forza UDP socket is ready.', flush=True)

    print(f'{SERVER_PROGRESS_STEPS[2]} Binding HTTP server on port {args.http_port}...', flush=True)
    try:
        httpd = NavigatorHTTPServer((args.host, args.http_port), NavigatorHandler)
    except OSError as exc:
        udp_sock.close()
        print(f'ERROR: HTTP port {args.http_port} is unavailable: {exc}')
        print('The browser was NOT opened. Close the process using that port and retry.')
        return 2
    print('      OK: HTTP server is ready. Startup complete.', flush=True)

    udp_thread = threading.Thread(
        target=udp_receiver,
        args=(state, udp_sock, stop),
        daemon=True,
        name='fh6-udp',
    )
    udp_thread.start()

    print('')
    print(f'FH6 Scenic Navigator v{APP_VERSION}')
    print('--------------------')
    print(f'PC:    http://127.0.0.1:{args.http_port}')
    print(f'PHONE: http://{lan_ip}:{args.http_port}')
    print(f'FORZA Data Out IP: {lan_ip}')
    print(f'FORZA Data Out Port: {args.udp_port}')
    print('Press Ctrl+C to stop.')
    print('')

    if args.open_browser:
        # Open only after BOTH HTTP and UDP sockets are successfully bound.
        threading.Timer(0.35, lambda: webbrowser.open(f'http://127.0.0.1:{args.http_port}')).start()

    try:
        httpd.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        print('\nStopping...')
    finally:
        stop.set()
        httpd.shutdown()
        httpd.server_close()
        udp_thread.join(timeout=1.0)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
