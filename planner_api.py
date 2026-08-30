from __future__ import annotations
import json
import queue
import re
import time
from urllib.parse import urlparse, parse_qs

from route_service import RouteRevisionConflict, RouteNotFound, RouteItemNotFound, RouteReverseConflict
from route_optimizer import NoValidOptimizedRoute
from navigation_service import NavigationSessionNotFound


class PlannerAPI:
    def __init__(self, route_service, events, places_service=None, navigation_service=None, io_service=None, diagnostics_provider=None):
        self.routes=route_service; self.events=events; self.places=places_service; self.navigation=navigation_service; self.io=io_service; self.diagnostics_provider=diagnostics_provider

    def _body(self, h):
        try: n=int(h.headers.get('Content-Length','0') or 0)
        except ValueError: n=0
        if not n: return {}
        raw=h.rfile.read(n)
        if not raw: return {}
        return json.loads(raw.decode('utf-8'))

    def _ok(self,h,payload,status=200): h._json(payload,status=status)

    def handle(self,h,method,path):
        try:
            return self._handle(h,method,path)
        except RouteRevisionConflict as exc:
            self._ok(h,{'error':'ROUTE_REVISION_CONFLICT','expected_revision':exc.expected,'actual_revision':exc.actual},409); return True
        except (NoValidOptimizedRoute, RouteReverseConflict) as exc:
            self._ok(h,{'error':'UNRESOLVED_ROUTE','detail':str(exc)},422); return True
        except (RouteNotFound,RouteItemNotFound,NavigationSessionNotFound) as exc:
            self._ok(h,{'error':'NOT_FOUND','detail':str(exc)},404); return True
        except (ValueError,json.JSONDecodeError) as exc:
            self._ok(h,{'error':'BAD_REQUEST','detail':str(exc)},400); return True

    def _route_event(self,route):
        self.events.publish('route.updated',{'route_id':route['id'],'revision':route['revision']})
        return route

    def _navigation_event(self,snapshot,action):
        sid=(snapshot or {}).get('session',{}).get('id') if snapshot else None
        payload={'session_id':sid,'action':action}
        if snapshot:
            payload['route_id']=snapshot['session']['route_id']; payload['current_item_id']=snapshot['session'].get('current_item_id')
        self.events.publish('navigation.updated',payload)
        return snapshot

    def _handle(self,h,method,path):
        if path=='/api/events' and method=='GET':
            self._serve_events(h); return True
        if path=='/api/backup/export' and method=='GET' and self.io is not None:
            self._ok(h,self.io.export_backup()); return True
        if path=='/api/backup/import' and method=='POST' and self.io is not None:
            out=self.io.import_backup(self._body(h));
            for rid in out.get('imported_route_ids',[]): self.events.publish('route.updated',{'route_id':rid,'revision':0})
            self._ok(h,out); return True
        if path=='/api/routes/import' and method=='POST' and self.io is not None:
            out=self.io.import_route(self._body(h)); r=out.get('route') or {};
            if r:self.events.publish('route.updated',{'route_id':r.get('id'),'revision':r.get('revision',0)})
            self._ok(h,out); return True
        if path=='/api/diagnostics' and method=='GET' and self.diagnostics_provider is not None:
            self._ok(h,self.diagnostics_provider()); return True
        m_export=re.fullmatch(r'/api/routes/([^/]+)/export',path)
        if m_export and method=='GET' and self.io is not None:
            self._ok(h,self.io.export_route(m_export.group(1))); return True
        if path=='/api/navigation/active' and method=='GET' and self.navigation is not None:
            self._ok(h,self.navigation.get_active()); return True
        if path=='/api/navigation/start' and method=='POST' and self.navigation is not None:
            b=self._body(h); snap=self.navigation.start(b.get('route_id'),b.get('start_anchor')); self._ok(h,self._navigation_event(snap,'started')); return True
        if path in ('/api/navigation/skip','/api/navigation/previous','/api/navigation/stop','/api/navigation/reached') and method=='POST' and self.navigation is not None:
            b=self._body(h); sid=b.get('session_id')
            if not sid:
                active=self.navigation.get_active(); sid=(active or {}).get('session',{}).get('id')
            if not sid: raise NavigationSessionNotFound('active')
            if path.endswith('/skip'): snap=self.navigation.skip(sid); action='skipped'
            elif path.endswith('/previous'): snap=self.navigation.previous(sid); action='previous'
            elif path.endswith('/stop'): snap=self.navigation.stop(sid); action='stopped'
            else:
                snap=self.navigation.complete_if_reached(sid,distance_m=b.get('distance_m',1e9),on_legal_leg=bool(b.get('on_legal_leg')),route_item_id=b.get('route_item_id')); action='progressed'
            self._ok(h,self._navigation_event(snap,action)); return True
        if path=='/api/places' and method=='GET' and self.places is not None:
            qs=parse_qs(urlparse(h.path).query); mode=(qs.get('mode') or ['recommended'])[0]
            self._ok(h,{'places':self.places.list_places(mode=mode),'catalog':self.places.catalog_info()}); return True
        m=re.fullmatch(r'/api/places/(.+)',path)
        if m and method=='GET' and self.places is not None:
            self._ok(h,self.places.get_place(m.group(1))); return True
        m=re.fullmatch(r'/api/favorites/(.+)',path)
        if m and method in ('POST','DELETE') and self.places is not None:
            p=self.places.set_favorite(m.group(1),method=='POST'); self.events.publish('favorite.updated',{'place_id':m.group(1),'favorite':method=='POST'}); self._ok(h,p); return True
        if path=='/api/user-places' and method=='POST' and self.places is not None:
            p=self.places.create_user_place(self._body(h)); self.events.publish('place.updated',{'place_id':p['id'],'action':'created'}); self._ok(h,p); return True
        m=re.fullmatch(r'/api/user-places/(.+)',path)
        if m and method=='PATCH' and self.places is not None:
            p=self.places.update_user_place(m.group(1),self._body(h)); self.events.publish('place.updated',{'place_id':p['id'],'action':'updated'}); self._ok(h,p); return True
        if m and method=='DELETE' and self.places is not None:
            b=self._body(h); result=self.places.delete_user_place(m.group(1),bool(b.get('force',False))); self.events.publish('place.updated',{'place_id':m.group(1),'action':'deleted'}); self._ok(h,result); return True
        if path=='/api/snap' and method=='GET' and self.places is not None:
            qs=parse_qs(urlparse(h.path).query); x=float((qs.get('x') or [0])[0]); y=float((qs.get('y') or [0])[0]); z=float((qs.get('z') or [0])[0]); anchor,dist=self.places.snap(x,y,z); self._ok(h,{'anchor_point_id':anchor,'snap_distance_m':dist}); return True
        if path=='/api/routes' and method=='GET':
            self._ok(h,{'built_in':self.routes.list_builtin_routes(),'routes':self.routes.list_routes()}); return True
        if path=='/api/routes' and method=='POST':
            b=self._body(h); r=self.routes.create_route(b.get('name') or 'Draft Route',bool(b.get('is_draft',True)),bool(b.get('make_active',True)))
            self._route_event(r); self._ok(h,r); return True
        if path=='/api/routes/active' and method=='GET':
            self._ok(h,self.routes.get_active_route()); return True
        m=re.fullmatch(r'/api/routes/([^/]+)/duplicate',path)
        if m and method=='POST':
            r=self.routes.duplicate_route(m.group(1)); self.events.publish('route.updated',{'route_id':r['id'],'revision':r['revision']}); self._ok(h,r); return True
        m=re.fullmatch(r'/api/routes/([^/]+)/preview',path)
        if m and method=='GET':
            if self.routes.preview_service is None:
                self._ok(h,{'error':'ROUTING_UNAVAILABLE'},503); return True
            qs=parse_qs(urlparse(h.path).query); start=(qs.get('start_anchor') or [None])[0]; start=None if start in (None,'') else int(start)
            route=self.routes.get_route(m.group(1)); self._ok(h,self.routes.preview_service.preview(route,start_anchor=start,objective=(qs.get('objective') or ['shortest'])[0])); return True
        m=re.fullmatch(r'/api/routes/([^/]+)/(reverse|optimize)',path)
        if m and method=='POST':
            b=self._body(h)
            if m.group(2)=='reverse': r=self.routes.reverse_route(m.group(1),b.get('expected_revision'),b.get('policy','cancel'))
            else: r=self.routes.optimize_route(m.group(1),b.get('expected_revision'),b.get('objective','fastest'),bool(b.get('keep_final',True)),bool(b.get('choose_orientation',True)),b.get('start_anchor'))
            self._route_event(r); self._ok(h,r); return True
        m=re.fullmatch(r'/api/routes/([^/]+)',path)
        if m and method=='GET': self._ok(h,self.routes.get_route(m.group(1))); return True
        if m and method=='PUT':
            b=self._body(h); r=self.routes.rename_route(m.group(1),b.get('name',''),b.get('expected_revision'),bool(b.get('make_saved',False))); self._route_event(r); self._ok(h,r); return True
        m=re.fullmatch(r'/api/routes/([^/]+)/items',path)
        if m and method=='POST':
            b=self._body(h); r=self.routes.add_item(m.group(1),b.get('item') or {},b.get('expected_revision'),b.get('position')); self._route_event(r); self._ok(h,r); return True
        m=re.fullmatch(r'/api/routes/([^/]+)/items/([^/]+)',path)
        if m and method=='PATCH':
            b=self._body(h)
            if 'position' in b:
                r=self.routes.move_item(m.group(1),m.group(2),b['position'],b.get('expected_revision'))
                patch={k:v for k,v in b.items() if k not in ('position','expected_revision')}
                if patch:
                    target_route_id=r['id']
                    target_item_id=m.group(2)
                    if target_route_id != m.group(1):
                        target=max(0,min(int(b['position']),len(r.get('items') or [])-1))
                        target_item_id=r['items'][target]['id']
                    r=self.routes.update_item(target_route_id,target_item_id,patch,r['revision'])
            else:
                patch={k:v for k,v in b.items() if k!='expected_revision'}; r=self.routes.update_item(m.group(1),m.group(2),patch,b.get('expected_revision'))
            self._route_event(r); self._ok(h,r); return True
        if m and method=='DELETE':
            b=self._body(h); r=self.routes.remove_item(m.group(1),m.group(2),b.get('expected_revision')); self._route_event(r); self._ok(h,r); return True
        m=re.fullmatch(r'/api/routes/([^/]+)/(undo|redo)',path)
        if m and method=='POST':
            b=self._body(h); fn=self.routes.undo if m.group(2)=='undo' else self.routes.redo; r=fn(m.group(1),b.get('expected_revision')); self._route_event(r); self._ok(h,r); return True
        m=re.fullmatch(r'/api/routes/([^/]+)/active',path)
        if m and method=='POST':
            r=self.routes.set_active(m.group(1)); self.events.publish('active_route.updated',{'route_id':r['id'],'revision':r['revision']}); self._ok(h,r); return True
        return False

    def _serve_events(self,h):
        h.send_response(200)
        h.send_header('Content-Type','text/event-stream; charset=utf-8')
        h.send_header('Cache-Control','no-cache')
        h.send_header('Connection','keep-alive')
        h.end_headers()
        try:
            h.wfile.write(b': connected\n\n'); h.wfile.flush()
            with self.events.subscribe() as q:
                while True:
                    try:
                        evt=q.get(timeout=15)
                        data=json.dumps(evt['payload'],ensure_ascii=False,separators=(',',':'))
                        block=f"id: {evt['id']}\nevent: {evt['type']}\ndata: {data}\n\n".encode('utf-8')
                    except queue.Empty:
                        block=b': heartbeat\n\n'
                    h.wfile.write(block); h.wfile.flush()
        except (BrokenPipeError,ConnectionResetError,OSError):
            return
