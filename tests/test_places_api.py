import gzip,json,tempfile,unittest
from pathlib import Path


class PlacesApiServiceTests(unittest.TestCase):
    def setUp(self):
        from planner_database import PlannerDatabase
        from places_service import PlacesService
        self.tmp=tempfile.TemporaryDirectory(); root=Path(self.tmp.name)
        b=root/'b.json'; c=root/'c.json'
        b.write_text(json.dumps({'schema_version':1,'catalog_version':'x','places':[{'id':'builtin.game.x','source':'game','kind':'point','name':'X','aliases':[],'category':'landmarks','subcategory':'landmark','tags':[],'position':{'x':3097.2,'y':151,'z':586.5},'navigation':{'anchor_point_id':0,'snap_distance_m':1},'surface':'asphalt','access':'easy','scenic_score':1,'default_visible':True,'featured':False,'quality':'verified'}]}))
        c.write_text(json.dumps({'schema_version':1,'catalog_version':'x','places':[],'blocks':[],'collections':[]}))
        self.db=PlannerDatabase(root/'db.sqlite'); self.db.initialize()
        self.svc=PlacesService(b,c,self.db,navgraph_path=Path('static/data/fh6_navgraph_v1.json.gz'))

    def tearDown(self): self.tmp.cleanup()

    def test_favorite_builtin_and_user_place_crud_with_resnap(self):
        self.svc.set_favorite('builtin.game.x',True)
        self.assertTrue(self.svc.get_place('builtin.game.x')['favorite'])
        u=self.svc.create_user_place({'name':'Mine','x':3097.3,'y':151,'z':586.6,'category':'my_place'})
        self.assertEqual(u['source'],'user'); self.assertIsNotNone(u['navigation']['anchor_point_id'])
        old=u['navigation']['anchor_point_id']
        moved=self.svc.update_user_place(u['id'],{'x':3119,'z':586.7})
        self.assertIsNotNone(moved['navigation']['anchor_point_id'])
        self.svc.set_favorite(u['id'],True); self.assertTrue(self.svc.get_place(u['id'])['favorite'])
        self.svc.delete_user_place(u['id'])
        with self.assertRaises(KeyError): self.svc.get_place(u['id'])

class PlacesHttpTests(unittest.TestCase):
    def test_planner_api_exposes_places_favorites_and_user_places(self):
        import threading, urllib.request, urllib.error
        from http.server import ThreadingHTTPServer
        from planner_database import PlannerDatabase
        from route_service import RouteService
        from planner_events import PlannerEventBus
        from planner_api import PlannerAPI
        from places_service import PlacesService
        from server import NavigatorHandler, TelemetryState
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); db=PlannerDatabase(root/'db.sqlite'); db.initialize()
            b=root/'b.json'; c=root/'c.json'
            b.write_text(json.dumps({'schema_version':1,'catalog_version':'x','places':[{'id':'builtin.game.x','source':'game','kind':'point','name':'X','aliases':[],'category':'landmarks','subcategory':'landmark','tags':[],'position':{'x':3097.2,'y':151,'z':586.5},'navigation':{'anchor_point_id':0,'snap_distance_m':1},'surface':'asphalt','access':'easy','scenic_score':1,'default_visible':True,'featured':False,'quality':'verified'}]}))
            c.write_text(json.dumps({'schema_version':1,'catalog_version':'x','places':[],'blocks':[],'collections':[]}))
            ps=PlacesService(b,c,db,Path('static/data/fh6_navgraph_v1.json.gz')); bus=PlannerEventBus(); api=PlannerAPI(RouteService(db),bus,ps)
            class Handler(NavigatorHandler): planner_api=api; state=TelemetryState()
            httpd=ThreadingHTTPServer(('127.0.0.1',0),Handler); th=threading.Thread(target=httpd.serve_forever,daemon=True); th.start(); base=f'http://127.0.0.1:{httpd.server_port}'
            def req(path,method='GET',payload=None):
                data=None if payload is None else json.dumps(payload).encode(); r=urllib.request.Request(base+path,data=data,method=method,headers={'Content-Type':'application/json'})
                with urllib.request.urlopen(r,timeout=2) as res: return res.status,json.loads(res.read())
            try:
                st,p=req('/api/places?mode=recommended'); self.assertEqual(st,200); self.assertEqual(p['places'][0]['id'],'builtin.game.x')
                st,f=req('/api/favorites/builtin.game.x','POST'); self.assertTrue(f['favorite'])
                st,u=req('/api/user-places','POST',{'name':'Mine','x':3097.3,'y':151,'z':586.6}); self.assertEqual(u['source'],'user')
                st,uu=req('/api/user-places/'+u['id'],'PATCH',{'name':'Mine 2'}); self.assertEqual(uu['name'],'Mine 2')
                st,d=req('/api/user-places/'+u['id'],'DELETE'); self.assertEqual(d['deleted'],u['id'])
            finally:
                httpd.shutdown(); httpd.server_close(); th.join(timeout=1)
