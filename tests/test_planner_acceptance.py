import json
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from navigation_service import NavigationService
from planner_api import PlannerAPI
from planner_database import PlannerDatabase
from planner_events import PlannerEventBus
from route_preview import DirectedGraph, RoutePreviewService
from route_service import RouteService
from server import NavigatorHandler, TelemetryState
from test_route_preview import graph_doc


def _http(base, path, method='GET', payload=None):
    data = None if payload is None else json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(base + path, data=data, method=method, headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=2) as res:
            body = res.read()
            return res.status, (json.loads(body) if body else None)
    except urllib.error.HTTPError as exc:
        body = exc.read()
        return exc.code, (json.loads(body) if body else None)


def _server(db_path):
    db = PlannerDatabase(db_path); db.initialize()
    preview = RoutePreviewService(DirectedGraph.from_payload(graph_doc()))
    routes = RouteService(db, preview_service=preview)
    nav = NavigationService(db, routes, preview)
    bus = PlannerEventBus()
    api = PlannerAPI(routes, bus, navigation_service=nav)
    class Handler(NavigatorHandler):
        planner_api = api
        state = TelemetryState()
    httpd = ThreadingHTTPServer(('127.0.0.1',0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True); thread.start()
    return db, routes, nav, bus, httpd, thread, f'http://127.0.0.1:{httpd.server_port}'


def _stop(httpd, thread):
    httpd.shutdown(); httpd.server_close(); thread.join(timeout=2)


def test_acceptance_api_add_reorder_start_live_edit_and_progress():
    with tempfile.TemporaryDirectory() as td:
        _, routes, nav, bus, httpd, thread, base = _server(Path(td)/'navigator.db')
        try:
            status, route = _http(base,'/api/routes/active'); assert status == 200
            rid = route['id']
            status, r1 = _http(base,f'/api/routes/{rid}/items','POST',{'expected_revision':0,'item':{'type':'temporary','nav_anchor_point_id':1,'custom_label':'A'}}); assert status == 200
            status, r2 = _http(base,f'/api/routes/{rid}/items','POST',{'expected_revision':1,'item':{'type':'temporary','nav_anchor_point_id':3,'custom_label':'B'}}); assert status == 200
            first, second = r2['items'][0]['id'], r2['items'][1]['id']
            status, moved = _http(base,f'/api/routes/{rid}/items/{second}','PATCH',{'expected_revision':2,'position':0}); assert status == 200
            assert [x['id'] for x in moved['items']] == [second, first]
            # Order B->A cannot be started from point 0 on this directed graph, so restore A->B and prove fail-closed.
            status, bad_preview = _http(base,f'/api/routes/{rid}/preview?start_anchor=0'); assert status == 200 and bad_preview['resolved'] is False
            status, failed = _http(base,'/api/navigation/start','POST',{'route_id':rid,'start_anchor':0}); assert status == 400 and 'legal directed path' in failed['detail']
            status, restored = _http(base,f'/api/routes/{rid}/undo','POST',{'expected_revision':3}); assert status == 200
            status, preview = _http(base,f'/api/routes/{rid}/preview?start_anchor=0'); assert status == 200 and preview['resolved'] is True
            with bus.subscribe() as q:
                status, started = _http(base,'/api/navigation/start','POST',{'route_id':rid,'start_anchor':0}); assert status == 200
                evt = q.get(timeout=.5); assert evt['type'] == 'navigation.updated'
            sid = started['session']['id']; current = started['session']['current_item_id']
            # A live route edit must preserve active-session history and add the new future item as upcoming.
            current_route = routes.get_route(rid)
            status, edited = _http(base,f'/api/routes/{rid}/items','POST',{'expected_revision':current_route['revision'],'item':{'type':'temporary','nav_anchor_point_id':3,'custom_label':'C'}}); assert status == 200
            status, snap = _http(base,'/api/navigation/active'); assert status == 200
            by_id = {p['route_item_id']:p['status'] for p in snap['progress']}
            assert by_id[current] == 'active'
            assert by_id[edited['items'][-1]['id']] == 'upcoming'
            # Arrival only advances when both distance and legal-leg evidence are true.
            status, unchanged = _http(base,'/api/navigation/reached','POST',{'session_id':sid,'route_item_id':current,'distance_m':20,'on_legal_leg':False}); assert status == 200
            assert unchanged['session']['current_item_id'] == current
            status, advanced = _http(base,'/api/navigation/reached','POST',{'session_id':sid,'route_item_id':current,'distance_m':49.0,'on_legal_leg':True}); assert status == 200
            assert advanced['session']['current_item_id'] != current
        finally:
            _stop(httpd, thread)


def test_acceptance_optimize_is_one_revision_and_undo_restores_exact_order():
    from route_optimizer import optimize_items
    from test_route_optimizer import MatrixPreview
    with tempfile.TemporaryDirectory() as td:
        db = PlannerDatabase(Path(td)/'navigator.db'); db.initialize()
        costs={(0,1):20,(0,2):5,(1,2):3,(2,1):3}
        svc=RouteService(db,preview_service=MatrixPreview(costs))
        r=svc.get_active_route(); rid=r['id']
        r=svc.add_item(rid,{'type':'temporary','nav_anchor_point_id':1,'custom_label':'A'},0)
        r=svc.add_item(rid,{'type':'temporary','nav_anchor_point_id':2,'custom_label':'B'},1)
        before=[x['id'] for x in r['items']]
        optimized=svc.optimize_route(rid,2,start_anchor=0,keep_final=False)
        assert optimized['revision']==3
        assert [x['id'] for x in optimized['items']] != before
        undone=svc.undo(rid,3)
        assert [x['id'] for x in undone['items']] == before


def test_acceptance_draft_survives_database_restart():
    with tempfile.TemporaryDirectory() as td:
        path=Path(td)/'navigator.db'
        db=PlannerDatabase(path); db.initialize(); svc=RouteService(db)
        r=svc.get_active_route(); rid=r['id']
        r=svc.add_item(rid,{'type':'temporary','nav_anchor_point_id':42,'custom_label':'Persistent waypoint'},0)
        revision=r['revision']; item_id=r['items'][0]['id']
        # New DB/service objects model a server restart.
        db2=PlannerDatabase(path); db2.initialize(); svc2=RouteService(db2)
        restored=svc2.get_active_route()
        assert restored['id']==rid and restored['revision']==revision
        assert restored['items'][0]['id']==item_id
        assert restored['items'][0]['custom_label']=='Persistent waypoint'
