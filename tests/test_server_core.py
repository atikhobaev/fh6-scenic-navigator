import unittest

from server import DEFAULT_UDP_PORT, TelemetryState, tile_upstream_url


class ServerCoreTests(unittest.TestCase):
    def test_default_udp_port_matches_forza_setting(self):
        self.assertEqual(DEFAULT_UDP_PORT, 1234)

    def test_state_reports_disconnected_before_packets(self):
        state = TelemetryState()
        payload = state.snapshot()
        self.assertFalse(payload['connected'])
        self.assertIsNone(payload['packet'])

    def test_state_accepts_packet_and_reports_source(self):
        state = TelemetryState()
        state.update({'speedKmh': 42.0}, '192.168.1.9')
        payload = state.snapshot()
        self.assertTrue(payload['connected'])
        self.assertEqual(payload['packet']['speedKmh'], 42.0)
        self.assertEqual(payload['sourceIp'], '192.168.1.9')

    def test_mapgenie_url_uses_y_x_order(self):
        self.assertEqual(
            tile_upstream_url(14, 8155, 8133),
            'https://tiles.mapgenie.io/games/forza-horizon-6/one/default-v2/14/8133/8155.jpg'
        )


if __name__ == '__main__':
    unittest.main()

class NavGraphServerTests(unittest.TestCase):
    def test_navgraph_provider_reports_bundled_graph(self):
        from pathlib import Path
        provider_cls = getattr(__import__('server'), 'NavGraphProvider', None)
        self.assertTrue(callable(provider_cls))
        provider = provider_cls(Path('static/data/fh6_navgraph_v1.json.gz'))
        info = provider.info()
        self.assertTrue(info['available'])
        self.assertEqual(info['format'], 'fh6-navgraph-v1')
        self.assertTrue(info['capabilities']['directed_segments'])

    def test_api_navgraph_serves_json_with_gzip_content_encoding(self):
        import gzip, json, tempfile, threading, urllib.request
        from pathlib import Path
        from http.server import ThreadingHTTPServer
        import server as server_module

        payload={'format':'fh6-navgraph-v1','source':{'sha256':'x'},'capabilities':{'directed_segments':True},'points':[],'segments':[],'transitions':[]}
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'graph.json.gz'; path.write_bytes(gzip.compress(json.dumps(payload).encode()))
            old=server_module.NavigatorHandler.navgraph_provider
            server_module.NavigatorHandler.navgraph_provider=server_module.NavGraphProvider(path)
            server_module.NavigatorHandler.state=server_module.TelemetryState()
            httpd=ThreadingHTTPServer(('127.0.0.1',0),server_module.NavigatorHandler)
            thread=threading.Thread(target=httpd.serve_forever,daemon=True); thread.start()
            try:
                req=urllib.request.Request(f'http://127.0.0.1:{httpd.server_port}/api/navgraph',headers={'Accept-Encoding':'gzip'})
                with urllib.request.urlopen(req,timeout=2) as resp:
                    raw=resp.read()
                    self.assertEqual(resp.headers.get('Content-Encoding'),'gzip')
                self.assertEqual(json.loads(gzip.decompress(raw)),payload)
            finally:
                httpd.shutdown(); httpd.server_close(); thread.join(timeout=1)
                server_module.NavigatorHandler.navgraph_provider=old

class StaticFreshnessTests(unittest.TestCase):
    def test_build_version_is_exposed(self):
        import server as server_module
        self.assertEqual(server_module.APP_VERSION, '1.20.0')

    def test_server_progress_is_scoped_separately_from_launcher_progress(self):
        import server as server_module
        self.assertEqual(
            server_module.SERVER_PROGRESS_STEPS,
            ('[server 1/3]', '[server 2/3]', '[server 3/3]'),
        )

    def test_static_ui_assets_disable_browser_cache(self):
        import threading, urllib.request
        from http.server import ThreadingHTTPServer
        import server as server_module

        old_state = server_module.NavigatorHandler.state
        server_module.NavigatorHandler.state = server_module.TelemetryState()
        httpd = ThreadingHTTPServer(('127.0.0.1', 0), server_module.NavigatorHandler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            for path in ('/', '/app.js', '/planner/', '/planner/planner.js', '/planner/planner.css'):
                with urllib.request.urlopen(f'http://127.0.0.1:{httpd.server_port}{path}', timeout=2) as resp:
                    self.assertEqual(resp.headers.get('Cache-Control'), 'no-store', path)
        finally:
            httpd.shutdown(); httpd.server_close(); thread.join(timeout=1)
            server_module.NavigatorHandler.state = old_state

class ConsoleNoiseAndTileSafetyTests(unittest.TestCase):
    def test_quiet_http_server_suppresses_browser_disconnect_tracebacks(self):
        import contextlib
        import io
        import server as server_module

        httpd = object.__new__(server_module.NavigatorHTTPServer)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            try:
                raise ConnectionResetError(10054, 'browser cancelled request')
            except ConnectionResetError:
                httpd.handle_error(None, ('127.0.0.1', 12345))
        self.assertEqual(err.getvalue(), '')

    def test_favicon_request_does_not_log_or_return_404(self):
        import threading
        import urllib.request
        import server as server_module

        old_state = server_module.NavigatorHandler.state
        server_module.NavigatorHandler.state = server_module.TelemetryState()
        httpd = server_module.NavigatorHTTPServer(('127.0.0.1', 0), server_module.NavigatorHandler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{httpd.server_port}/favicon.ico', timeout=2) as resp:
                self.assertEqual(resp.status, 204)
        finally:
            httpd.shutdown(); httpd.server_close(); thread.join(timeout=1)
            server_module.NavigatorHandler.state = old_state

    def test_low_zoom_tile_requests_are_rejected_before_upstream_fetch(self):
        import threading
        import urllib.error
        import urllib.request
        import server as server_module

        old_state = server_module.NavigatorHandler.state
        server_module.NavigatorHandler.state = server_module.TelemetryState()
        httpd = server_module.NavigatorHTTPServer(('127.0.0.1', 0), server_module.NavigatorHandler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(f'http://127.0.0.1:{httpd.server_port}/maptile/10/507/508.jpg', timeout=2)
            self.assertEqual(ctx.exception.code, 400)
        finally:
            httpd.shutdown(); httpd.server_close(); thread.join(timeout=1)
            server_module.NavigatorHandler.state = old_state

class PortableDataRootTests(unittest.TestCase):
    def test_server_exposes_portable_user_data_root_constant(self):
        import server as server_module
        self.assertTrue(hasattr(server_module, 'USER_DATA_ROOT'))
