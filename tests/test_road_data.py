import unittest
import server


class RoadDataParsingTests(unittest.TestCase):
    def test_extracts_roads_array_from_forzalabs_html(self):
        html = '<script>const roads = [{"type":"asphalt","points":[{"x":1,"y":2},{"x":3,"y":4}]}]; const routeNodes = [];</script>'
        extractor = getattr(server, 'extract_js_value', lambda *_: None)
        self.assertEqual(
            extractor(html, 'roads'),
            '[{"type":"asphalt","points":[{"x":1,"y":2},{"x":3,"y":4}]}]'
        )


if __name__ == '__main__':
    unittest.main()

class RoadNetworkProviderTests(unittest.TestCase):
    def test_direct_json_source_is_cached_and_reused(self):
        import tempfile
        from pathlib import Path

        provider_cls = getattr(server, 'RoadNetworkProvider', None)
        self.assertTrue(callable(provider_cls), 'RoadNetworkProvider must exist')
        calls = []
        payload = b'{"source":"test","roads":[{"type":"asphalt","points":[{"x":1,"y":2},{"x":3,"y":4}]}]}'

        def fetch(url):
            calls.append(url)
            return payload

        with tempfile.TemporaryDirectory() as td:
            cache = Path(td) / 'roads.json'
            provider = provider_cls(cache_file=cache, fetch_bytes=fetch, allow_download=True)
            first = provider.get()
            second = provider.get()
            self.assertEqual(len(first['roads']), 1)
            self.assertEqual(second, first)
            self.assertEqual(len(calls), 1)
            self.assertTrue(cache.exists())


    def test_default_runtime_provider_uses_bundled_roads_without_network(self):
        from pathlib import Path
        provider = server.RoadNetworkProvider()
        data = provider.get()
        self.assertGreaterEqual(len(data["roads"]), 400)
        self.assertEqual(provider.cache_file, Path("static/data/fh6_roads.json").resolve())
        self.assertFalse(provider.allow_download)

    def test_offline_provider_fails_fast_when_bundled_roads_are_missing(self):
        import tempfile
        from pathlib import Path
        calls=[]
        with tempfile.TemporaryDirectory() as td:
            provider = server.RoadNetworkProvider(cache_file=Path(td)/"missing.json", fetch_bytes=lambda url: calls.append(url), allow_download=False)
            with self.assertRaisesRegex(OSError, "bundled FH6 road dataset is missing"):
                provider.get()
        self.assertEqual(calls, [])

class RoadNetworkHttpTests(unittest.TestCase):
    def test_api_roads_serves_provider_dataset(self):
        import json
        import threading
        import urllib.error
        import urllib.request
        from http.server import ThreadingHTTPServer

        class FakeProvider:
            def get(self):
                return {'source':'test','roads':[{'type':'asphalt','points':[{'x':1,'y':2},{'x':3,'y':4}]}]}

        server.NavigatorHandler.state = server.TelemetryState()
        server.NavigatorHandler.road_provider = FakeProvider()
        httpd = ThreadingHTTPServer(('127.0.0.1', 0), server.NavigatorHandler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            status = None
            body = b''
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{httpd.server_port}/api/roads', timeout=2) as response:
                    status = response.status
                    body = response.read()
            except urllib.error.HTTPError as exc:
                status = exc.code
                body = exc.read()
            self.assertEqual(status, 200)
            payload = json.loads(body)
            self.assertEqual(payload['source'], 'test')
            self.assertEqual(len(payload['roads']), 1)
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join(timeout=1)
