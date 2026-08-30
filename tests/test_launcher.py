import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import launcher


class _InfoHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path != '/api/info':
            self.send_error(404)
            return
        body = json.dumps({'name': 'FH6 Scenic Navigator', 'version': '1.16.1'}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class LauncherTests(unittest.TestCase):
    def test_probe_existing_navigator_identifies_old_build(self):
        httpd = ThreadingHTTPServer(('127.0.0.1', 0), _InfoHandler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            info = launcher.probe_existing_navigator(httpd.server_port)
            self.assertEqual(info['name'], 'FH6 Scenic Navigator')
            self.assertEqual(info['version'], '1.16.1')
            self.assertTrue(launcher.is_fh6_navigator(info))
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join(timeout=1)


    def test_existing_navigator_is_never_silently_reused(self):
        httpd = ThreadingHTTPServer(('127.0.0.1', 0), _InfoHandler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            with self.assertRaises(RuntimeError):
                launcher.stop_previous_navigator(httpd.server_port)
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join(timeout=1)

    def test_windows_netstat_parser_finds_8080_listener(self):
        sample = '''\n  TCP    0.0.0.0:8080           0.0.0.0:0              LISTENING       4242\n  TCP    127.0.0.1:8080         127.0.0.1:51000        ESTABLISHED     4242\n'''
        self.assertEqual(launcher.listener_pid_from_netstat(sample, 8080), 4242)


    def test_bundled_catalog_preflight_is_local_and_reports_coverage_limit(self):
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            data = root / 'static' / 'data'
            data.mkdir(parents=True)
            (data / 'builtin_places.json').write_text(json.dumps({
                'schema_version': 1,
                'places': [{'id': f'p{i}'} for i in range(24)],
                'build': {
                    'runtime_places': 24,
                    'reported_source_markers': 796,
                    'coordinate_records_captured': 24,
                    'coverage_limited_reason': 'bundled reviewed offline snapshot',
                },
            }), encoding='utf-8')
            (data / 'fh6_navgraph_v1.json.gz').write_bytes(b'local-graph')
            (data / 'fh6_roads.json').write_text('{"source":"local","roads":[{"points":[{"x":1,"y":2},{"x":3,"y":4}]}]}', encoding='utf-8')
            result = launcher.inspect_bundled_catalog(root=root)
            self.assertEqual(result['status'], 'ready')
            self.assertEqual(result['runtime_places'], 24)
            self.assertEqual(result['reported_source_markers'], 796)
            self.assertTrue(result['coverage_limited'])
            self.assertEqual(result['coverage_limited_reason'], 'bundled reviewed offline snapshot')

    def test_bundled_catalog_preflight_fails_fast_when_local_files_are_inconsistent(self):
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            data = root / 'static' / 'data'
            data.mkdir(parents=True)
            (data / 'builtin_places.json').write_text(json.dumps({
                'schema_version': 1,
                'places': [{'id': f'p{i}'} for i in range(3)],
                'build': {
                    'runtime_places': 24,
                    'reported_source_markers': 796,
                    'coordinate_records_captured': 24,
                    'coverage_limited_reason': 'bundled reviewed offline snapshot',
                },
            }), encoding='utf-8')
            (data / 'fh6_navgraph_v1.json.gz').write_bytes(b'local-graph')
            (data / 'fh6_roads.json').write_text('{"source":"local","roads":[{"points":[{"x":1,"y":2},{"x":3,"y":4}]}]}', encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError, 'bundled map catalog metadata mismatch'):
                launcher.inspect_bundled_catalog(root=root)

    def test_bundled_catalog_preflight_fails_fast_when_navgraph_is_missing(self):
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            data = root / 'static' / 'data'
            data.mkdir(parents=True)
            (data / 'builtin_places.json').write_text(json.dumps({
                'schema_version': 1,
                'places': [{'id': 'p1'}],
                'build': {'runtime_places': 1, 'reported_source_markers': 1, 'coordinate_records_captured': 1},
            }), encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError, 'bundled Directed WVAN graph is missing'):
                launcher.inspect_bundled_catalog(root=root)


    def test_bundled_catalog_preflight_fails_fast_when_road_dataset_is_missing(self):
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            data = root / 'static' / 'data'
            data.mkdir(parents=True)
            (data / 'builtin_places.json').write_text(json.dumps({
                'schema_version': 1,
                'places': [{'id': 'p1'}],
                'build': {'runtime_places': 1, 'reported_source_markers': 1, 'coordinate_records_captured': 1},
            }), encoding='utf-8')
            (data / 'fh6_navgraph_v1.json.gz').write_bytes(b'local-graph')
            with self.assertRaisesRegex(RuntimeError, 'bundled FH6 road dataset is missing'):
                launcher.inspect_bundled_catalog(root=root)

    def test_game_localization_cache_uses_installed_stringtables_when_available(self):
        from pathlib import Path
        import tempfile
        from unittest import mock
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); tables=root/'StringTables'; tables.mkdir()
            with mock.patch('game_localization.find_stringtables_dir', return_value=tables), mock.patch('game_localization.refresh_place_names', return_value={'game.a':{'en-US':'A','ru-RU':'А'}}) as refresh:
                result=launcher.refresh_game_localization_cache(root=root)
            refresh.assert_called_once_with(root/'static', tables)
            self.assertEqual(result['status'],'ready')
            self.assertEqual(result['localized_places'],1)

    def test_game_localization_cache_keeps_english_fallback_when_game_tables_are_missing(self):
        from pathlib import Path
        import tempfile
        from unittest import mock
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/'static'/'data').mkdir(parents=True)
            (root/'static'/'data'/'place_names.json').write_text('{}',encoding='utf-8')
            with mock.patch('game_localization.find_stringtables_dir', return_value=None), mock.patch('game_localization.refresh_place_names') as refresh:
                result=launcher.refresh_game_localization_cache(root=root)
            refresh.assert_not_called()
            self.assertEqual(result['status'],'fallback')
            self.assertEqual(result['localized_places'],0)
            self.assertIn('coverage',result)

    def test_windows_netstat_parser_ignores_other_ports(self):
        sample = '  TCP    0.0.0.0:9090           0.0.0.0:0              LISTENING       9999\n'
        self.assertIsNone(launcher.listener_pid_from_netstat(sample, 8080))


if __name__ == '__main__':
    unittest.main()

class NativeLauncherArgsTests(unittest.TestCase):
    def test_main_preflight_uses_same_http_port_as_server(self):
        from unittest import mock
        import server
        env={'FH6_NATIVE_LAUNCHER':'1','FH6_HTTP_PORT':'18080','FH6_UDP_PORT':'11234'}
        catalog={'runtime_places':796,'road_count':1,'coverage_limited':False}
        localization={'status':'fallback','coverage':{}}
        with mock.patch.dict('os.environ',env,clear=False), \
             mock.patch('launcher.stop_previous_navigator',return_value=False) as stop, \
             mock.patch('launcher.inspect_bundled_catalog',return_value=catalog), \
             mock.patch('launcher.refresh_game_localization_cache',return_value=localization), \
             mock.patch.object(server,'main',return_value=0) as server_main:
            self.assertEqual(launcher.main(),0)
        stop.assert_called_once_with(18080)
        server_main.assert_called_once_with(['--http-port','18080','--udp-port','11234'])

    def test_native_launcher_disables_browser_and_uses_port_env(self):
        env={'FH6_NATIVE_LAUNCHER':'1','FH6_HTTP_PORT':'18080','FH6_UDP_PORT':'11234'}
        self.assertEqual(launcher.server_args_from_env(env), ['--http-port','18080','--udp-port','11234'])
