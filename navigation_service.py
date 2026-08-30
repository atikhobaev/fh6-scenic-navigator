from __future__ import annotations

import uuid
from planner_database import PlannerDatabase, utc_now


class NavigationSessionNotFound(KeyError):
    pass


class NavigationService:
    """Persistent progress for one concrete drive of a saved/active Route."""
    def __init__(self, db: PlannerDatabase, routes, preview_service):
        self.db=db; self.routes=routes; self.preview_service=preview_service

    def _session_row(self, con, session_id):
        row=con.execute('select * from navigation_sessions where id=?',(session_id,)).fetchone()
        if not row: raise NavigationSessionNotFound(session_id)
        return row

    def _active_id(self, con):
        row=con.execute("select value from app_state where key='active_navigation_session_id'").fetchone()
        return row['value'] if row and row['value'] else None

    def _set_active_id(self, con, value):
        if value is None:
            con.execute("delete from app_state where key='active_navigation_session_id'")
        else:
            con.execute("insert into app_state(key,value) values('active_navigation_session_id',?) on conflict(key) do update set value=excluded.value",(value,))

    def _session_dict(self,row):
        return {k:row[k] for k in row.keys()}

    def _route_progress(self, con, session_id, route_items):
        rows={r['route_item_id']:dict(r) for r in con.execute('select * from navigation_progress where session_id=?',(session_id,)).fetchall()}
        return [rows[i['id']] for i in route_items if i['id'] in rows]

    def _target_for_item(self, item):
        typ=item.get('type')
        if typ in ('scenic_road','scenic_loop'):
            if self.preview_service.places is None: return None
            block=self.preview_service.places.get_scenic_block(item['scenic_block_id'])
            direction=item.get('direction') or ('clockwise' if typ=='scenic_loop' else 'forward')
            fixed=self.preview_service._fixed_scenic(block,direction)
            if not fixed:return None
            entry=self.preview_service.graph.points.get(fixed['entry']); exit_=self.preview_service.graph.points.get(fixed['exit'])
            if not entry or not exit_:return None
            return {'route_item_id':item['id'],'type':typ,'anchor_point_id':fixed['exit'],'entry_anchor_point_id':fixed['entry'],'world':{'x':exit_[0],'y':exit_[1],'z':exit_[2]},'entry_world':{'x':entry[0],'y':entry[1],'z':entry[2]},'fixed_segment_ids':list(fixed['segment_ids']),'fixed_point_ids':list(fixed['point_ids'])}
        anchor=self.preview_service._anchor_for_item(item)
        if anchor is None:return None
        world=self.preview_service.graph.points.get(int(anchor))
        if world is None:return None
        return {'route_item_id':item['id'],'type':typ,'anchor_point_id':int(anchor),'world':{'x':world[0],'y':world[1],'z':world[2]},'fixed_segment_ids':[],'fixed_point_ids':[int(anchor)]}

    def start(self, route_id=None, start_anchor=None):
        route=self.routes.get_route(route_id) if route_id else self.routes.get_active_route()
        if not route['items']: raise ValueError('route has no destinations')
        preview=self.preview_service.preview(route,start_anchor=start_anchor,objective='shortest')
        if not preview.get('resolved'):
            raise ValueError('route has no legal directed path')
        sid=f'nav.{uuid.uuid4()}'; now=utc_now(); first=route['items'][0]['id']
        with self.db.transaction() as con:
            old=self._active_id(con)
            if old:
                con.execute('update navigation_sessions set finished_at=coalesce(finished_at,?) where id=?',(now,old))
            con.execute('insert into navigation_sessions(id,route_id,route_revision_started,started_at,finished_at,current_item_id) values(?,?,?,?,?,?)',(sid,route['id'],route['revision'],now,None,first))
            for idx,item in enumerate(route['items']):
                con.execute('insert into navigation_progress(session_id,route_item_id,status,visited_at) values(?,?,?,?)',(sid,item['id'],'active' if idx==0 else 'upcoming',None))
            self._set_active_id(con,sid)
        return self.snapshot(sid)

    def get_active(self):
        with self.db.connect() as con: sid=self._active_id(con)
        return None if not sid else self.snapshot(sid)

    def snapshot(self, session_id):
        route_id=None
        with self.db.connect() as con:
            row=self._session_row(con,session_id); route_id=row['route_id']
        route=self.routes.get_route(route_id)
        self._reconcile(session_id,route)
        with self.db.connect() as con:
            row=self._session_row(con,session_id)
            progress=self._route_progress(con,session_id,route['items'])
        targets=[t for t in (self._target_for_item(item) for item in route['items']) if t is not None]
        current=next((t for t in targets if t['route_item_id']==row['current_item_id']),None)
        preview=self.preview_service.preview(route,objective='shortest')
        return {'session':self._session_dict(row),'route':route,'progress':progress,'targets':targets,'current_target':current,'preview':preview}

    def _reconcile(self, session_id, route):
        items=route['items']; ids=[i['id'] for i in items]
        with self.db.transaction() as con:
            s=self._session_row(con,session_id)
            if s['finished_at']: return
            existing={r['route_item_id']:dict(r) for r in con.execute('select * from navigation_progress where session_id=?',(session_id,)).fetchall()}
            current=s['current_item_id']
            current_idx=ids.index(current) if current in ids else None
            for idx,item in enumerate(items):
                iid=item['id']
                if iid in existing: continue
                # Items introduced behind the current target are intentionally not resurrected.
                status='skipped' if current_idx is not None and idx<current_idx else 'upcoming'
                con.execute('insert into navigation_progress(session_id,route_item_id,status,visited_at) values(?,?,?,NULL)',(session_id,iid,status))
                existing[iid]={'route_item_id':iid,'status':status}
            if current not in ids:
                next_id=next((iid for iid in ids if existing.get(iid,{}).get('status') not in ('visited','skipped')),None)
                con.execute('update navigation_progress set status=? where session_id=? and route_item_id=?',('active',session_id,next_id)) if next_id else None
                con.execute('update navigation_sessions set current_item_id=?,finished_at=? where id=?',(next_id,None if next_id else utc_now(),session_id))

    def _advance(self, session_id, completed_status):
        snap=self.snapshot(session_id); route=snap['route']; current=snap['session']['current_item_id']
        if not current:return snap
        ids=[x['id'] for x in route['items']]; idx=ids.index(current) if current in ids else -1
        progress={p['route_item_id']:p for p in snap['progress']}; next_id=next((iid for iid in ids[idx+1:] if progress.get(iid,{}).get('status') not in ('visited','skipped')),None)
        now=utc_now()
        with self.db.transaction() as con:
            con.execute('update navigation_progress set status=?,visited_at=? where session_id=? and route_item_id=?',(completed_status,now if completed_status=='visited' else None,session_id,current))
            if next_id:
                con.execute("update navigation_progress set status='active',visited_at=NULL where session_id=? and route_item_id=?",(session_id,next_id))
                con.execute('update navigation_sessions set current_item_id=? where id=?',(next_id,session_id))
            else:
                con.execute('update navigation_sessions set current_item_id=NULL,finished_at=? where id=?',(now,session_id)); self._set_active_id(con,None)
        return self.snapshot(session_id)

    def skip(self, session_id):
        return self._advance(session_id,'skipped')

    def previous(self, session_id):
        snap=self.snapshot(session_id); route=snap['route']; current=snap['session']['current_item_id']; ids=[x['id'] for x in route['items']]
        if not current or current not in ids:return snap
        idx=ids.index(current); progress={p['route_item_id']:p for p in snap['progress']}
        prev=next((iid for iid in reversed(ids[:idx]) if progress.get(iid,{}).get('status') in ('visited','skipped')),None)
        if not prev:return snap
        with self.db.transaction() as con:
            con.execute("update navigation_progress set status='upcoming',visited_at=NULL where session_id=? and route_item_id=?",(session_id,current))
            con.execute("update navigation_progress set status='active',visited_at=NULL where session_id=? and route_item_id=?",(session_id,prev))
            con.execute('update navigation_sessions set current_item_id=?,finished_at=NULL where id=?',(prev,session_id)); self._set_active_id(con,session_id)
        return self.snapshot(session_id)

    def complete_if_reached(self, session_id, *, distance_m, on_legal_leg, route_item_id=None):
        snap=self.snapshot(session_id); current=snap['session']['current_item_id']
        if current is None:return snap
        if route_item_id is not None and route_item_id != current:return snap
        if not on_legal_leg or float(distance_m)>50.0:return snap
        return self._advance(session_id,'visited')

    def stop(self, session_id):
        now=utc_now()
        with self.db.transaction() as con:
            self._session_row(con,session_id)
            con.execute('update navigation_sessions set finished_at=coalesce(finished_at,?),current_item_id=NULL where id=?',(now,session_id))
            if self._active_id(con)==session_id:self._set_active_id(con,None)
        # snapshot after finished state; reconciliation is a no-op for finished sessions.
        return self.snapshot(session_id)
