import tempfile, unittest
from pathlib import Path

from planner_database import PlannerDatabase
from route_service import RouteService
from route_preview import DirectedGraph, RoutePreviewService
from test_route_preview import graph_doc


class NavigationServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.db=PlannerDatabase(Path(self.tmp.name)/'nav.db'); self.db.initialize()
        self.preview=RoutePreviewService(DirectedGraph.from_payload(graph_doc()))
        self.routes=RouteService(self.db,preview_service=self.preview)
        r=self.routes.get_active_route(); self.rid=r['id']
        r=self.routes.add_item(self.rid,{'type':'temporary','nav_anchor_point_id':1,'custom_label':'A'},0)
        r=self.routes.add_item(self.rid,{'type':'temporary','nav_anchor_point_id':2,'custom_label':'B'},1)
        r=self.routes.add_item(self.rid,{'type':'temporary','nav_anchor_point_id':3,'custom_label':'C'},2)
        self.route=self.routes.get_route(self.rid)
    def tearDown(self): self.tmp.cleanup()

    def service(self):
        from navigation_service import NavigationService
        return NavigationService(self.db,self.routes,self.preview)

    def test_start_requires_resolved_preview_and_repeat_sessions_are_independent(self):
        svc=self.service(); s1=svc.start(self.rid,start_anchor=0)
        self.assertEqual([p['status'] for p in s1['progress']],['active','upcoming','upcoming'])
        self.assertEqual(s1['current_target']['anchor_point_id'],1)
        self.assertEqual((s1['current_target']['world']['x'],s1['current_target']['world']['z']),(10.0,0.0))
        self.assertEqual(len(s1['targets']),3)
        first=s1['session']['id']; svc.skip(first)
        s2=svc.start(self.rid,start_anchor=0)
        self.assertNotEqual(first,s2['session']['id'])
        self.assertEqual([p['status'] for p in s2['progress']],['active','upcoming','upcoming'])
        bad=self.routes.create_route('Bad',False,False); bad=self.routes.add_item(bad['id'],{'type':'temporary','nav_anchor_point_id':3},0); bad=self.routes.add_item(bad['id'],{'type':'temporary','nav_anchor_point_id':0},1)
        with self.assertRaisesRegex(ValueError,'legal directed path'):
            svc.start(bad['id'],start_anchor=3)

    def test_skip_previous_and_route_edit_reconciliation(self):
        svc=self.service(); snap=svc.start(self.rid,start_anchor=0); sid=snap['session']['id']; ids=[x['id'] for x in self.route['items']]
        after=svc.skip(sid); self.assertEqual(after['session']['current_item_id'],ids[1]); self.assertEqual(after['progress'][0]['status'],'skipped')
        prev=svc.previous(sid); self.assertEqual(prev['session']['current_item_id'],ids[0]); self.assertEqual(prev['progress'][0]['status'],'active')
        # Move to B, then delete B while navigation is active. C must become active, not resurrect A.
        svc.skip(sid); route=self.routes.get_route(self.rid); self.routes.remove_item(self.rid,ids[1],route['revision'])
        reconciled=svc.snapshot(sid)
        self.assertEqual(reconciled['session']['current_item_id'],ids[2])
        # A new future item inserted after C is upcoming and existing progress is preserved.
        route=self.routes.get_route(self.rid); route=self.routes.add_item(self.rid,{'type':'temporary','nav_anchor_point_id':3,'custom_label':'D'},route['revision'])
        reconciled=svc.snapshot(sid); by={p['route_item_id']:p['status'] for p in reconciled['progress']}
        self.assertEqual(by[ids[0]],'skipped'); self.assertEqual(by[ids[2]],'active'); self.assertEqual(by[route['items'][-1]['id']],'upcoming')

    def test_completion_requires_50m_and_correct_legal_leg(self):
        svc=self.service(); snap=svc.start(self.rid,start_anchor=0); sid=snap['session']['id']; first=snap['session']['current_item_id']
        for distance,on_leg in [(51,True),(20,False)]:
            unchanged=svc.complete_if_reached(sid,distance_m=distance,on_legal_leg=on_leg,route_item_id=first)
            self.assertEqual(unchanged['session']['current_item_id'],first)
        advanced=svc.complete_if_reached(sid,distance_m=49.9,on_legal_leg=True,route_item_id=first)
        self.assertNotEqual(advanced['session']['current_item_id'],first)
        self.assertEqual(next(p for p in advanced['progress'] if p['route_item_id']==first)['status'],'visited')

    def test_stop_finishes_session_and_clears_active_pointer(self):
        svc=self.service(); snap=svc.start(self.rid,start_anchor=0); sid=snap['session']['id']
        stopped=svc.stop(sid); self.assertIsNotNone(stopped['session']['finished_at']); self.assertIsNone(svc.get_active())

if __name__=='__main__': unittest.main()

class NavigationApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.db=PlannerDatabase(Path(self.tmp.name)/"api.db"); self.db.initialize()
        self.preview=RoutePreviewService(DirectedGraph.from_payload(graph_doc())); self.routes=RouteService(self.db,preview_service=self.preview)
        r=self.routes.get_active_route(); self.rid=r["id"]
        r=self.routes.add_item(self.rid,{"type":"temporary","nav_anchor_point_id":1},0)
        self.routes.add_item(self.rid,{"type":"temporary","nav_anchor_point_id":2},1)
    def tearDown(self): self.tmp.cleanup()
    def test_navigation_http_contract_and_events(self):
        import json, threading, urllib.request
        from http.server import ThreadingHTTPServer
        from planner_events import PlannerEventBus
        from planner_api import PlannerAPI
        from navigation_service import NavigationService
        from server import NavigatorHandler, TelemetryState
        bus=PlannerEventBus(); nav=NavigationService(self.db,self.routes,self.preview); api=PlannerAPI(self.routes,bus,navigation_service=nav)
        class Handler(NavigatorHandler): planner_api=api; state=TelemetryState()
        h=ThreadingHTTPServer(('127.0.0.1',0),Handler); th=threading.Thread(target=h.serve_forever,daemon=True); th.start(); base=f'http://127.0.0.1:{h.server_port}'
        def req(path,method='GET',payload=None):
            data=None if payload is None else json.dumps(payload).encode(); q=urllib.request.Request(base+path,data=data,method=method,headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(q,timeout=2) as r:return json.loads(r.read())
        try:
            with bus.subscribe() as q:
                started=req('/api/navigation/start','POST',{'route_id':self.rid,'start_anchor':0}); sid=started['session']['id']
                evt=q.get(timeout=.5); self.assertEqual(evt['type'],'navigation.updated')
            active=req('/api/navigation/active'); self.assertEqual(active['session']['id'],sid)
            skipped=req('/api/navigation/skip','POST',{'session_id':sid}); self.assertEqual(skipped['progress'][0]['status'],'skipped')
            previous=req('/api/navigation/previous','POST',{'session_id':sid}); self.assertEqual(previous['progress'][0]['status'],'active')
            first=previous['session']['current_item_id']; reached=req('/api/navigation/reached','POST',{'session_id':sid,'route_item_id':first,'distance_m':20,'on_legal_leg':True}); self.assertNotEqual(reached['session']['current_item_id'],first)
            stopped=req('/api/navigation/stop','POST',{'session_id':sid}); self.assertIsNotNone(stopped['session']['finished_at'])
            self.assertIsNone(req('/api/navigation/active'))
        finally: h.shutdown(); h.server_close(); th.join(timeout=1)
