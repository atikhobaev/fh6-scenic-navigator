import json, tempfile, unittest
from pathlib import Path

class PlannerIOTests(unittest.TestCase):
    def setUp(self):
        from planner_database import PlannerDatabase
        from route_service import RouteService
        from places_service import PlacesService
        from planner_io import PlannerIO
        self.tmp=tempfile.TemporaryDirectory(); root=Path(self.tmp.name)
        self.builtin=root/'builtin.json'; self.curated=root/'curated.json'
        self.builtin.write_text(json.dumps({'schema_version':1,'catalog_version':'t','places':[
          {'id':'builtin.game.house.a','source':'game','kind':'point','name':'House A','aliases':[],'category':'houses','subcategory':'','tags':[],'position':{'x':0,'y':0,'z':0},'navigation':{'anchor_point_id':1,'snap_distance_m':1},'surface':'asphalt','access':'easy','scenic_score':1,'default_visible':True,'featured':False,'quality':'verified'}]}),encoding='utf-8')
        self.curated.write_text(json.dumps({'schema_version':1,'catalog_version':'t','places':[],'blocks':[],'collections':[]}),encoding='utf-8')
        self.db=PlannerDatabase(root/'db.sqlite'); self.db.initialize(); self.routes=RouteService(self.db); self.places=PlacesService(self.builtin,self.curated,self.db); self.io=PlannerIO(self.db,self.routes,self.places)

    def tearDown(self): self.tmp.cleanup()

    def _seed(self):
        user=self.places.create_user_place({'name':'My View','x':12,'y':0,'z':34})
        self.places.set_favorite('builtin.game.house.a',True); self.places.set_favorite(user['id'],True)
        r=self.routes.get_active_route(); r=self.routes.rename_route(r['id'],'Mountain Tour',r['revision'],make_saved=True)
        r=self.routes.add_item(r['id'],{'type':'place','place_id':'builtin.game.house.a'},r['revision'])
        r=self.routes.add_item(r['id'],{'type':'place','place_id':user['id']},r['revision'])
        return user,r

    def test_backup_round_trip_includes_user_places_favorites_and_stable_builtin_ids(self):
        user,r=self._seed(); doc=self.io.export_backup()
        self.assertEqual(doc['format'],'fh6-navigator-backup'); self.assertEqual(doc['format_version'],1)
        self.assertIn(user['id'],{p['id'] for p in doc['user_places']})
        self.assertIn('builtin.game.house.a',doc['favorites'])
        item_ids=[i.get('place_id') for x in doc['routes'] for i in x['items']]
        self.assertIn('builtin.game.house.a',item_ids)
        # Importing the same backup twice must never collide with existing route/user IDs.
        a=self.io.import_backup(doc); b=self.io.import_backup(doc)
        self.assertTrue(a['imported_route_ids']); self.assertTrue(b['imported_route_ids'])
        self.assertTrue(set(a['imported_route_ids']).isdisjoint(b['imported_route_ids']))

    def test_route_export_import_includes_referenced_user_place_and_is_duplicate_safe(self):
        user,r=self._seed(); doc=self.io.export_route(r['id'])
        self.assertEqual(doc['format'],'fh6route'); self.assertEqual(doc['format_version'],1)
        self.assertEqual([p['name'] for p in doc['user_places']],['My View'])
        a=self.io.import_route(doc); b=self.io.import_route(doc)
        self.assertNotEqual(a['route']['id'],b['route']['id'])
        self.assertEqual(a['route']['name'],'Mountain Tour')

    def test_missing_builtin_reference_is_reported_but_existing_data_is_not_destroyed(self):
        _,r=self._seed(); doc=self.io.export_route(r['id']); doc['route']['items'][0]['place_id']='builtin.game.missing'
        before=len(self.routes.list_routes()); out=self.io.import_route(doc)
        self.assertGreater(len(self.routes.list_routes()),before)
        self.assertIn('builtin.game.missing',out['warnings'][0])

    def test_unsupported_format_version_is_rejected_before_mutation(self):
        before=len(self.routes.list_routes())
        with self.assertRaises(ValueError): self.io.import_backup({'format':'fh6-navigator-backup','format_version':999})
        self.assertEqual(len(self.routes.list_routes()),before)

if __name__=='__main__': unittest.main()
