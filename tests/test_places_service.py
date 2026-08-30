import json, tempfile, unittest
from pathlib import Path


class PlacesServiceTests(unittest.TestCase):
    def setUp(self):
        from planner_database import PlannerDatabase
        from places_service import PlacesService
        self.tmp=tempfile.TemporaryDirectory(); root=Path(self.tmp.name)
        self.builtin=root/'builtin.json'; self.curated=root/'curated.json'
        self.builtin.write_text(json.dumps({'schema_version':1,'catalog_version':'test','places':[
            {'id':'builtin.game.house.a','source':'game','kind':'point','name':'House A','aliases':['Casa A'],'category':'houses','subcategory':'player_house','tags':['home'],'position':{'x':0,'y':0,'z':0},'navigation':{'anchor_point_id':0,'snap_distance_m':1},'surface':'asphalt','access':'easy','scenic_score':1,'default_visible':True,'featured':False,'quality':'verified'},
            {'id':'builtin.game.board.b','source':'game','kind':'point','name':'Board B','aliases':[],'category':'collectibles','subcategory':'board','tags':['board'],'position':{'x':10,'y':0,'z':0},'navigation':{'anchor_point_id':1,'snap_distance_m':2},'surface':'asphalt','access':'easy','scenic_score':0,'default_visible':False,'featured':False,'quality':'verified'}
        ]}),encoding='utf-8')
        self.curated.write_text(json.dumps({'schema_version':1,'catalog_version':'test','places':[
            {'id':'curated.place.view','source':'curated','kind':'point','name':'Volcano View','aliases':['Viewpoint'],'category':'scenic_places','subcategory':'viewpoint','tags':['mountain','volcano'],'position':{'x':20,'y':0,'z':0},'navigation':{'anchor_point_id':2,'snap_distance_m':3},'surface':'asphalt','access':'easy','scenic_score':5,'default_visible':True,'featured':True,'quality':'reviewed'}
        ],'blocks':[],'collections':[]}),encoding='utf-8')
        self.db=PlannerDatabase(root/'db.sqlite'); self.db.initialize()
        self.svc=PlacesService(self.builtin,self.curated,self.db)

    def tearDown(self): self.tmp.cleanup()

    def test_recommended_and_all_modes_merge_sources(self):
        recommended=self.svc.list_places(mode='recommended')
        self.assertEqual({p['id'] for p in recommended},{'builtin.game.house.a','curated.place.view'})
        allp=self.svc.list_places(mode='all')
        self.assertIn('builtin.game.board.b',{p['id'] for p in allp})

    def test_lookup_and_catalog_info(self):
        p=self.svc.get_place('curated.place.view'); self.assertEqual(p['source'],'curated')
        info=self.svc.catalog_info(); self.assertEqual(info['total'],3); self.assertEqual(info['recommended'],2)

    def test_duplicate_ids_fail_closed(self):
        from places_service import CatalogValidationError, PlacesService
        data=json.loads(self.curated.read_text()); data['places'][0]['id']='builtin.game.house.a'; self.curated.write_text(json.dumps(data))
        with self.assertRaises(CatalogValidationError): PlacesService(self.builtin,self.curated,self.db)
