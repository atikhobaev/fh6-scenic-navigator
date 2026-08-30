import tempfile
import unittest
from pathlib import Path


class RouteServiceTests(unittest.TestCase):
    def setUp(self):
        from planner_database import PlannerDatabase
        from route_service import RouteService
        self.tmp = tempfile.TemporaryDirectory()
        self.db = PlannerDatabase(Path(self.tmp.name) / 'navigator.db'); self.db.initialize()
        self.svc = RouteService(self.db)

    def tearDown(self): self.tmp.cleanup()

    def test_add_move_remove_are_revisioned_and_use_stable_item_ids(self):
        route = self.svc.get_active_route()
        r1 = self.svc.add_item(route['id'], {'type':'temporary','temporary_x':1,'temporary_y':2,'temporary_z':3,'nav_anchor_point_id':10}, expected_revision=0)
        item_id = r1['items'][0]['id']
        r2 = self.svc.add_item(route['id'], {'type':'temporary','temporary_x':4,'temporary_y':5,'temporary_z':6,'nav_anchor_point_id':11}, expected_revision=1)
        self.assertEqual(r2['revision'], 2)
        r3 = self.svc.move_item(route['id'], item_id, 1, expected_revision=2)
        self.assertEqual(r3['items'][1]['id'], item_id)
        r4 = self.svc.remove_item(route['id'], item_id, expected_revision=3)
        self.assertEqual(r4['revision'], 4)
        self.assertNotIn(item_id, [i['id'] for i in r4['items']])

    def test_stale_revision_rejected_without_mutation(self):
        from route_service import RouteRevisionConflict
        route = self.svc.get_active_route()
        self.svc.add_item(route['id'], {'type':'temporary','nav_anchor_point_id':1}, expected_revision=0)
        with self.assertRaises(RouteRevisionConflict):
            self.svc.add_item(route['id'], {'type':'temporary','nav_anchor_point_id':2}, expected_revision=0)
        self.assertEqual(len(self.svc.get_active_route()['items']), 1)

    def test_undo_redo_restore_same_item_and_position(self):
        r = self.svc.get_active_route()
        a = self.svc.add_item(r['id'], {'type':'temporary','nav_anchor_point_id':1}, expected_revision=0)
        first = a['items'][0]['id']
        b = self.svc.add_item(r['id'], {'type':'temporary','nav_anchor_point_id':2}, expected_revision=1)
        second = b['items'][1]['id']
        c = self.svc.move_item(r['id'], first, 1, expected_revision=2)
        self.assertEqual([x['id'] for x in c['items']], [second, first])
        u = self.svc.undo(r['id'], expected_revision=3)
        self.assertEqual([x['id'] for x in u['items']], [first, second])
        rr = self.svc.redo(r['id'], expected_revision=4)
        self.assertEqual([x['id'] for x in rr['items']], [second, first])
        self.assertEqual(rr['revision'], 5)

    def test_saved_routes_duplicate_and_single_active_route(self):
        r = self.svc.get_active_route()
        named = self.svc.rename_route(r['id'], 'Mountain Tour', expected_revision=0, make_saved=True)
        copy = self.svc.duplicate_route(named['id'])
        self.svc.set_active(copy['id'])
        self.assertEqual(self.svc.get_active_route()['id'], copy['id'])
        self.assertEqual(copy['name'], 'Mountain Tour copy')
        self.assertGreaterEqual(len(self.svc.list_routes()), 2)
