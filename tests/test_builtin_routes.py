import json
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from planner_database import PlannerDatabase
from route_preview import DirectedGraph, RoutePreviewService
from route_service import RouteService
from test_route_preview import graph_doc


class BuiltinRouteProviderTests(unittest.TestCase):
    def test_real_grand_tour_is_virtual_read_only_and_has_27_resolved_places(self):
        from builtin_routes import BuiltinRouteProvider, GRAND_TOUR_ID

        provider = BuiltinRouteProvider(
            Path('static/route.json'),
            Path('static/data/scenic_catalog.json'),
        )
        route = provider.get(GRAND_TOUR_ID)

        self.assertEqual(route['id'], GRAND_TOUR_ID)
        self.assertEqual(route['name'], 'Grand Tour Japan')
        self.assertTrue(route['read_only'])
        self.assertTrue(route['built_in'])
        self.assertEqual(route['revision'], 0)
        self.assertEqual(len(route['items']), 27)
        self.assertTrue(all(item['place_id'] for item in route['items']))
        self.assertTrue(all(isinstance(item['nav_anchor_point_id'], int) for item in route['items']))

    def test_route_service_opens_builtin_without_sqlite_route_and_first_edit_creates_active_copy(self):
        from builtin_routes import BuiltinRouteProvider, GRAND_TOUR_ID

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            route_path, places_path = self._write_small_catalog(root)
            db = PlannerDatabase(root / 'navigator.db')
            db.initialize()
            provider = BuiltinRouteProvider(route_path, places_path)
            svc = RouteService(db, builtin_routes=provider)

            opened = svc.set_active(GRAND_TOUR_ID)
            self.assertTrue(opened['read_only'])
            with db.connect() as con:
                count = con.execute('select count(*) from routes where id=?', (GRAND_TOUR_ID,)).fetchone()[0]
            self.assertEqual(count, 0)

            original_first = opened['items'][0]['id']
            edited = svc.move_item(GRAND_TOUR_ID, original_first, 1, expected_revision=0)

            self.assertNotEqual(edited['id'], GRAND_TOUR_ID)
            self.assertEqual(edited['name'], 'Grand Tour Japan — Copy')
            self.assertFalse(edited['read_only'])
            self.assertEqual(edited['revision'], 1)
            self.assertEqual(svc.get_active_route()['id'], edited['id'])
            self.assertEqual(provider.get(GRAND_TOUR_ID)['items'][0]['id'], original_first)
            self.assertEqual(provider.get(GRAND_TOUR_ID)['revision'], 0)

    def test_builtin_route_can_start_navigation_without_materializing_route_row(self):
        from builtin_routes import BuiltinRouteProvider, GRAND_TOUR_ID
        from navigation_service import NavigationService

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            route_path, places_path = self._write_small_catalog(root)
            db = PlannerDatabase(root / 'navigator.db')
            db.initialize()
            preview = RoutePreviewService(DirectedGraph.from_payload(graph_doc()))
            provider = BuiltinRouteProvider(route_path, places_path)
            routes = RouteService(db, preview_service=preview, builtin_routes=provider)
            navigation = NavigationService(db, routes, preview)

            snap = navigation.start(GRAND_TOUR_ID, start_anchor=0)

            self.assertEqual(snap['session']['route_id'], GRAND_TOUR_ID)
            self.assertTrue(snap['route']['read_only'])
            self.assertEqual(len(snap['progress']), 2)
            with db.connect() as con:
                count = con.execute('select count(*) from routes where id=?', (GRAND_TOUR_ID,)).fetchone()[0]
            self.assertEqual(count, 0)

    def test_combined_move_and_patch_edits_one_copy_not_two(self):
        from builtin_routes import BuiltinRouteProvider, GRAND_TOUR_ID
        from planner_api import PlannerAPI
        from planner_events import PlannerEventBus
        from server import NavigatorHandler, TelemetryState

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            route_path, places_path = self._write_small_catalog(root)
            db = PlannerDatabase(root / 'navigator.db'); db.initialize()
            routes = RouteService(db, builtin_routes=BuiltinRouteProvider(route_path, places_path))
            api = PlannerAPI(routes, PlannerEventBus())
            class Handler(NavigatorHandler):
                planner_api = api
                state = TelemetryState()
            httpd = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
            thread = threading.Thread(target=httpd.serve_forever, daemon=True); thread.start()
            try:
                original = routes.get_route(GRAND_TOUR_ID)
                item_id = original['items'][0]['id']
                payload = json.dumps({'expected_revision': 0, 'position': 1, 'custom_label': 'Moved A'}).encode()
                req = urllib.request.Request(
                    f'http://127.0.0.1:{httpd.server_port}/api/routes/{GRAND_TOUR_ID}/items/{item_id}',
                    data=payload,
                    method='PATCH',
                    headers={'Content-Type': 'application/json'},
                )
                with urllib.request.urlopen(req, timeout=2) as response:
                    edited = json.loads(response.read())
            finally:
                httpd.shutdown(); httpd.server_close(); thread.join(timeout=1)

            self.assertNotEqual(edited['id'], GRAND_TOUR_ID)
            self.assertEqual(edited['revision'], 2)
            self.assertEqual(edited['items'][1]['custom_label'], 'Moved A')
            with db.connect() as con:
                copies = con.execute("select count(*) from routes where name='Grand Tour Japan — Copy'").fetchone()[0]
            self.assertEqual(copies, 1)

    @staticmethod
    def _write_small_catalog(root: Path):
        route_path = root / 'route.json'
        places_path = root / 'places.json'
        route_path.write_text(json.dumps({
            'name': 'Legacy label',
            'loop': False,
            'waypoints': [
                {'name': 'A RU', 'game': 'A'},
                {'name': 'B RU', 'game': 'B'},
            ],
        }), encoding='utf-8')
        places_path.write_text(json.dumps({
            'places': [
                {'id': 'curated.place.a', 'name': 'A', 'aliases': ['A RU'], 'navigation': {'anchor_point_id': 1}},
                {'id': 'curated.place.b', 'name': 'B', 'aliases': ['B RU'], 'navigation': {'anchor_point_id': 2}},
            ]
        }), encoding='utf-8')
        return route_path, places_path


if __name__ == '__main__':
    unittest.main()
