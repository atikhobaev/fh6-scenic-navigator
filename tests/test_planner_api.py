import json
import queue
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path


class PlannerEventBusTests(unittest.TestCase):
    def test_publish_reaches_subscriber(self):
        from planner_events import PlannerEventBus
        bus=PlannerEventBus()
        with bus.subscribe() as q:
            bus.publish('route.updated', {'route_id':'r','revision':2})
            evt=q.get(timeout=0.2)
        self.assertEqual(evt['type'],'route.updated')
        self.assertEqual(evt['payload']['revision'],2)


class PlannerHttpTests(unittest.TestCase):
    def setUp(self):
        from planner_database import PlannerDatabase
        from route_service import RouteService
        from planner_events import PlannerEventBus
        from planner_api import PlannerAPI
        from server import NavigatorHandler, TelemetryState
        self.tmp=tempfile.TemporaryDirectory()
        db=PlannerDatabase(Path(self.tmp.name)/'navigator.db'); db.initialize()
        self.bus=PlannerEventBus()
        api=PlannerAPI(RouteService(db), self.bus)
        class Handler(NavigatorHandler):
            planner_api=api
            state=TelemetryState()
        self.httpd=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.httpd.serve_forever,daemon=True); self.thread.start()
        self.base=f'http://127.0.0.1:{self.httpd.server_port}'

    def tearDown(self):
        self.httpd.shutdown(); self.httpd.server_close(); self.thread.join(timeout=1); self.tmp.cleanup()

    def req(self,path,method='GET',payload=None):
        data=None if payload is None else json.dumps(payload).encode()
        req=urllib.request.Request(self.base+path,data=data,method=method,headers={'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=2) as r:
                return r.status,json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return e.code,json.loads(e.read().decode())

    def test_create_add_move_remove_undo_redo_and_conflict(self):
        status,active=self.req('/api/routes/active'); self.assertEqual(status,200)
        rid=active['id']
        status,r1=self.req(f'/api/routes/{rid}/items','POST',{'expected_revision':0,'item':{'type':'temporary','nav_anchor_point_id':1}})
        self.assertEqual((status,r1['revision']),(200,1)); iid=r1['items'][0]['id']
        status,conflict=self.req(f'/api/routes/{rid}/items','POST',{'expected_revision':0,'item':{'type':'temporary','nav_anchor_point_id':2}})
        self.assertEqual(status,409); self.assertEqual(conflict['error'],'ROUTE_REVISION_CONFLICT')
        status,r2=self.req(f'/api/routes/{rid}/items','POST',{'expected_revision':1,'item':{'type':'temporary','nav_anchor_point_id':2}})
        second=r2['items'][1]['id']
        status,r3=self.req(f'/api/routes/{rid}/items/{iid}','PATCH',{'expected_revision':2,'position':1})
        self.assertEqual([x['id'] for x in r3['items']],[second,iid])
        status,u=self.req(f'/api/routes/{rid}/undo','POST',{'expected_revision':3})
        self.assertEqual([x['id'] for x in u['items']],[iid,second])
        status,rr=self.req(f'/api/routes/{rid}/redo','POST',{'expected_revision':4})
        self.assertEqual([x['id'] for x in rr['items']],[second,iid])
        status,removed=self.req(f'/api/routes/{rid}/items/{iid}','DELETE',{'expected_revision':5})
        self.assertEqual(len(removed['items']),1)

    def test_route_create_list_and_rename(self):
        status,new=self.req('/api/routes','POST',{'name':'Night Drive','is_draft':False})
        self.assertEqual(status,200)
        status,renamed=self.req(f"/api/routes/{new['id']}",'PUT',{'expected_revision':0,'name':'Night City','make_saved':True})
        self.assertEqual(renamed['name'],'Night City')
        status,routes=self.req('/api/routes'); self.assertTrue(any(x['id']==new['id'] for x in routes['routes']))

class PlannerBootstrapTests(unittest.TestCase):
    def test_default_planner_api_creates_persistent_database(self):
        import server
        from builtin_routes import GRAND_TOUR_ID
        with tempfile.TemporaryDirectory() as td:
            api = server.create_default_planner_api(Path(td) / 'navigator.db')
            route = api.routes.get_active_route()
            self.assertEqual(route['name'], 'Draft Route')
            self.assertTrue((Path(td) / 'navigator.db').is_file())
            builtins = api.routes.list_builtin_routes()
            self.assertEqual([r['id'] for r in builtins], [GRAND_TOUR_ID])
            self.assertTrue(builtins[0]['read_only'])
            self.assertEqual(api.places.catalog_info()['community_version'], '2026-08-29-evidence-only')

class PlannerRoutingApiTests(unittest.TestCase):
    def test_preview_reverse_and_optimize_endpoints_exist(self):
        import threading, urllib.request, urllib.error
        from http.server import ThreadingHTTPServer
        from planner_database import PlannerDatabase
        from route_service import RouteService
        from planner_events import PlannerEventBus
        from planner_api import PlannerAPI
        from route_preview import DirectedGraph, RoutePreviewService
        from test_route_preview import graph_doc
        from server import NavigatorHandler, TelemetryState
        with tempfile.TemporaryDirectory() as td:
            db=PlannerDatabase(Path(td)/'db.sqlite'); db.initialize(); preview=RoutePreviewService(DirectedGraph.from_payload(graph_doc()))
            routes=RouteService(db,preview_service=preview); api=PlannerAPI(routes,PlannerEventBus())
            route=routes.get_active_route(); routes.add_item(route['id'],{'type':'temporary','nav_anchor_point_id':0},0); routes.add_item(route['id'],{'type':'temporary','nav_anchor_point_id':3},1)
            class Handler(NavigatorHandler): planner_api=api; state=TelemetryState()
            h=ThreadingHTTPServer(('127.0.0.1',0),Handler); th=threading.Thread(target=h.serve_forever,daemon=True); th.start(); base=f'http://127.0.0.1:{h.server_port}'
            def req(path,method='GET',payload=None):
                data=None if payload is None else json.dumps(payload).encode(); r=urllib.request.Request(base+path,data=data,method=method,headers={'Content-Type':'application/json'})
                with urllib.request.urlopen(r,timeout=2) as res:return res.status,json.loads(res.read())
            try:
                st,p=req(f"/api/routes/{route['id']}/preview"); self.assertTrue(p['resolved'])
                st,r=req(f"/api/routes/{route['id']}/reverse",'POST',{'expected_revision':2,'policy':'keep'}); self.assertEqual(r['revision'],3)
                # Optimization may fail because reversed route 3->0 is illegal; API must fail closed, not invent a path.
                try: req(f"/api/routes/{route['id']}/optimize",'POST',{'expected_revision':3,'start_anchor':0})
                except urllib.error.HTTPError as e: self.assertEqual(e.code,422)
            finally: h.shutdown(); h.server_close(); th.join(timeout=1)

class PlannerIoApiSurfaceTests(unittest.TestCase):
    def test_backup_route_export_import_and_diagnostics_endpoints(self):
        from planner_database import PlannerDatabase
        from route_service import RouteService
        from places_service import PlacesService
        from planner_io import PlannerIO
        from planner_events import PlannerEventBus
        from planner_api import PlannerAPI
        from server import NavigatorHandler,TelemetryState
        import gzip
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); b=root/'b.json'; c=root/'c.json'; g=root/'g.json.gz'
            b.write_text(json.dumps({'schema_version':1,'catalog_version':'x','places':[{'id':'builtin.a','source':'game','kind':'point','name':'A','aliases':[],'category':'landmarks','subcategory':'','tags':[],'position':{'x':0,'y':0,'z':0},'navigation':{'anchor_point_id':1,'snap_distance_m':0},'surface':'asphalt','access':'easy','scenic_score':1,'default_visible':True,'featured':False,'quality':'verified'}]}))
            c.write_text(json.dumps({'schema_version':1,'catalog_version':'x','places':[],'blocks':[],'collections':[]}))
            gp={'format':'fh6-navgraph-v1','capabilities':{'directed_segments':True,'turn_transitions':True},'points':[[1,0,0,0],[2,1,0,0]],'segments':[[1,0,1,2,1,1,'asphalt']],'transitions':[]}
            g.write_bytes(gzip.compress(json.dumps(gp).encode()))
            db=PlannerDatabase(root/'db.sqlite');db.initialize();routes=RouteService(db);places=PlacesService(b,c,db,g);io=PlannerIO(db,routes,places)
            api=PlannerAPI(routes,PlannerEventBus(),places_service=places,io_service=io,diagnostics_provider=lambda:{'valid':True,'places':1})
            class Handler(NavigatorHandler):planner_api=api;state=TelemetryState()
            h=ThreadingHTTPServer(('127.0.0.1',0),Handler);th=threading.Thread(target=h.serve_forever,daemon=True);th.start();base=f'http://127.0.0.1:{h.server_port}'
            def req(path,method='GET',payload=None):
                data=None if payload is None else json.dumps(payload).encode();q=urllib.request.Request(base+path,data=data,method=method,headers={'Content-Type':'application/json'})
                with urllib.request.urlopen(q,timeout=2) as res:return res.status,json.loads(res.read())
            try:
                st,backup=req('/api/backup/export');self.assertEqual(backup['format'],'fh6-navigator-backup')
                st,imp=req('/api/backup/import','POST',backup);self.assertIn('imported_route_ids',imp)
                rid=routes.get_active_route()['id'];st,rdoc=req(f'/api/routes/{rid}/export');self.assertEqual(rdoc['format'],'fh6route')
                st,rimp=req('/api/routes/import','POST',rdoc);self.assertIn('route',rimp)
                st,diag=req('/api/diagnostics');self.assertTrue(diag['valid'])
            finally:h.shutdown();h.server_close();th.join(timeout=1)
