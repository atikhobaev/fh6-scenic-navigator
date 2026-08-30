from __future__ import annotations

from copy import deepcopy
import json
import sqlite3
import uuid

from planner_database import PlannerDatabase, utc_now


class RouteRevisionConflict(RuntimeError):
    def __init__(self, expected: int, actual: int):
        super().__init__(f'route revision conflict: expected {expected}, actual {actual}')
        self.expected = expected
        self.actual = actual


class RouteNotFound(KeyError): pass
class RouteItemNotFound(KeyError): pass
class RouteReverseConflict(RuntimeError): pass


class RouteService:
    def __init__(self, db: PlannerDatabase, graph_provider=None, preview_service=None, builtin_routes=None):
        self.db = db
        self.graph_provider = graph_provider
        self.preview_service = preview_service
        self.builtin_routes = builtin_routes

    def _is_builtin(self, route_id):
        return bool(self.builtin_routes and self.builtin_routes.has(route_id))

    def _route_row(self, con, route_id):
        row = con.execute('select * from routes where id=?', (route_id,)).fetchone()
        if not row: raise RouteNotFound(route_id)
        return row

    def _canonical(self, con, route_id):
        r = self._route_row(con, route_id)
        items = [dict(x) for x in con.execute('select * from route_items where route_id=? order by position,id', (route_id,)).fetchall()]
        for it in items:
            it['position_locked'] = bool(it['position_locked'])
            it['direction_locked'] = bool(it['direction_locked'])
        return {
            'id': r['id'], 'name': r['name'], 'is_draft': bool(r['is_draft']), 'revision': int(r['revision']),
            'created_at': r['created_at'], 'updated_at': r['updated_at'], 'last_opened_at': r['last_opened_at'],
            'read_only': False, 'built_in': False,
            'items': items,
        }

    def _state(self, con, route_id):
        c = self._canonical(con, route_id)
        return {'name': c['name'], 'is_draft': c['is_draft'], 'items': c['items']}

    def _assert_revision(self, con, route_id, expected):
        actual = int(self._route_row(con, route_id)['revision'])
        if expected is not None and int(expected) != actual:
            raise RouteRevisionConflict(int(expected), actual)
        return actual

    def _replace_state(self, con, route_id, state):
        now = utc_now()
        con.execute('update routes set name=?,is_draft=?,updated_at=? where id=?', (state['name'], 1 if state.get('is_draft',False) else 0, now, route_id))
        con.execute('delete from route_items where route_id=?', (route_id,))
        for pos, item in enumerate(state.get('items', [])):
            self._insert_item(con, route_id, pos, item, preserve_id=True)

    def _record(self, con, route_id, old_revision, action, before, after, clear_redo=True):
        if clear_redo:
            con.execute("delete from route_revisions where route_id=? and is_undone=1", (route_id,))
        new_revision = old_revision + 1
        now = utc_now()
        con.execute('update routes set revision=?,updated_at=? where id=?', (new_revision, now, route_id))
        con.execute(
            'insert into route_revisions(route_id,revision_number,action,before_json,after_json,is_undone,created_at) values(?,?,?,?,?,?,?)',
            (route_id,new_revision,action,json.dumps(before,separators=(',',':')),json.dumps(after,separators=(',',':')),0,now),
        )
        return new_revision

    def list_routes(self):
        with self.db.connect() as con:
            ids = [r['id'] for r in con.execute('select id from routes order by last_opened_at desc, created_at desc').fetchall()]
            return [self._canonical(con, rid) for rid in ids]

    def list_builtin_routes(self):
        return self.builtin_routes.list_routes() if self.builtin_routes else []

    def get_route(self, route_id):
        if self._is_builtin(route_id):
            return self.builtin_routes.get(route_id)
        with self.db.connect() as con: return self._canonical(con, route_id)

    def get_active_route(self):
        state = self.db.get_app_state(); rid = state.get('active_route_id')
        if not rid: raise RouteNotFound('active')
        return self.get_route(rid)

    def create_route(self, name='Draft Route', is_draft=True, make_active=True):
        rid=f'route.{uuid.uuid4()}'; now=utc_now()
        with self.db.transaction() as con:
            con.execute('insert into routes(id,name,is_draft,revision,created_at,updated_at,last_opened_at) values(?,?,?,?,?,?,?)',(rid,name,1 if is_draft else 0,0,now,now,now))
            if make_active:
                con.execute("insert into app_state(key,value) values('active_route_id',?) on conflict(key) do update set value=excluded.value",(rid,))
            return self._canonical(con,rid)

    def set_active(self, route_id):
        if self._is_builtin(route_id):
            with self.db.transaction() as con:
                con.execute("insert into app_state(key,value) values('active_route_id',?) on conflict(key) do update set value=excluded.value",(route_id,))
            return self.builtin_routes.get(route_id)
        with self.db.transaction() as con:
            self._route_row(con,route_id)
            now=utc_now(); con.execute('update routes set last_opened_at=? where id=?',(now,route_id))
            con.execute("insert into app_state(key,value) values('active_route_id',?) on conflict(key) do update set value=excluded.value",(route_id,))
            return self._canonical(con,route_id)

    def _copy_builtin_into(self, con, route_id, *, make_active):
        src = self.builtin_routes.get(route_id)
        rid = f'route.{uuid.uuid4()}'
        now = utc_now()
        con.execute(
            'insert into routes(id,name,is_draft,revision,created_at,updated_at,last_opened_at) values(?,?,?,?,?,?,?)',
            (rid, src['name'] + ' — Copy', 0, 0, now, now, now),
        )
        item_ids = {}
        for pos, item in enumerate(src['items']):
            clone = dict(item)
            old_id = clone.get('id')
            clone['id'] = f'item.{uuid.uuid4()}'
            item_ids[old_id] = clone['id']
            self._insert_item(con, rid, pos, clone, preserve_id=True)
        if make_active:
            con.execute(
                "insert into app_state(key,value) values('active_route_id',?) on conflict(key) do update set value=excluded.value",
                (rid,),
            )
        return rid, item_ids

    def _prepare_edit(self, con, route_id, expected_revision=None, item_id=None):
        if self._is_builtin(route_id):
            actual = int(self.builtin_routes.get(route_id)['revision'])
            if expected_revision is not None and int(expected_revision) != actual:
                raise RouteRevisionConflict(int(expected_revision), actual)
            rid, item_ids = self._copy_builtin_into(con, route_id, make_active=True)
            return rid, item_ids.get(item_id, item_id), 0
        return route_id, item_id, self._assert_revision(con, route_id, expected_revision)

    def rename_route(self, route_id, name, expected_revision=None, make_saved=False):
        name=(name or '').strip()
        if not name: raise ValueError('route name is required')
        with self.db.transaction() as con:
            route_id, _, rev = self._prepare_edit(con, route_id, expected_revision)
            before=self._state(con,route_id)
            con.execute('update routes set name=?,is_draft=? where id=?',(name,0 if make_saved else int(before['is_draft']),route_id))
            after=self._state(con,route_id); self._record(con,route_id,rev,'rename_route',before,after)
            return self._canonical(con,route_id)

    def duplicate_route(self, route_id):
        with self.db.transaction() as con:
            src=self.builtin_routes.get(route_id) if self._is_builtin(route_id) else self._canonical(con,route_id)
            rid=f'route.{uuid.uuid4()}'; now=utc_now()
            suffix=' — Copy' if src.get('read_only') else ' copy'
            con.execute('insert into routes(id,name,is_draft,revision,created_at,updated_at,last_opened_at) values(?,?,?,?,?,?,?)',(rid,src['name']+suffix,0,0,now,now,now))
            for pos,item in enumerate(src['items']):
                clone=dict(item); clone['id']=f'item.{uuid.uuid4()}'
                self._insert_item(con,rid,pos,clone,preserve_id=True)
            return self._canonical(con,rid)

    def _insert_item(self, con, route_id, position, item, preserve_id=False):
        iid = item.get('id') if preserve_id else None
        iid = iid or f'item.{uuid.uuid4()}'
        typ=item.get('type','temporary')
        con.execute('''insert into route_items(
          id,route_id,position,type,place_id,temporary_x,temporary_y,temporary_z,nav_anchor_point_id,scenic_block_id,direction,stop_type,position_locked,direction_locked,custom_label
        ) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(
            iid,route_id,position,typ,item.get('place_id'),item.get('temporary_x'),item.get('temporary_y'),item.get('temporary_z'),item.get('nav_anchor_point_id'),item.get('scenic_block_id'),item.get('direction'),item.get('stop_type','stop'),1 if item.get('position_locked') else 0,1 if item.get('direction_locked') else 0,item.get('custom_label')
        ))
        return iid

    def _normalize_positions(self, con, route_id):
        rows=con.execute('select id from route_items where route_id=? order by position,id',(route_id,)).fetchall()
        for pos,row in enumerate(rows):
            con.execute('update route_items set position=? where id=?',(pos+100000,row['id']))
        for pos,row in enumerate(rows):
            con.execute('update route_items set position=? where id=?',(pos,row['id']))

    def add_item(self, route_id, item, expected_revision=None, position=None):
        with self.db.transaction() as con:
            route_id, _, rev = self._prepare_edit(con, route_id, expected_revision)
            before=self._state(con,route_id)
            count=con.execute('select count(*) from route_items where route_id=?',(route_id,)).fetchone()[0]
            target=count if position is None else max(0,min(int(position),count))
            rows=[dict(r) for r in con.execute('select * from route_items where route_id=? order by position,id',(route_id,)).fetchall()]
            new=dict(item); new['id']=f'item.{uuid.uuid4()}'
            rows.insert(target,new)
            con.execute('delete from route_items where route_id=?',(route_id,))
            for pos,it in enumerate(rows): self._insert_item(con,route_id,pos,it,preserve_id=True)
            after=self._state(con,route_id); self._record(con,route_id,rev,'add_item',before,after)
            return self._canonical(con,route_id)

    def move_item(self, route_id, item_id, new_position, expected_revision=None):
        with self.db.transaction() as con:
            route_id, item_id, rev = self._prepare_edit(con, route_id, expected_revision, item_id)
            before=self._state(con,route_id)
            rows=[dict(r) for r in con.execute('select * from route_items where route_id=? order by position,id',(route_id,)).fetchall()]
            idx=next((i for i,x in enumerate(rows) if x['id']==item_id),None)
            if idx is None: raise RouteItemNotFound(item_id)
            item=rows.pop(idx); target=max(0,min(int(new_position),len(rows))); rows.insert(target,item)
            con.execute('delete from route_items where route_id=?',(route_id,))
            for pos,it in enumerate(rows): self._insert_item(con,route_id,pos,it,preserve_id=True)
            after=self._state(con,route_id); self._record(con,route_id,rev,'move_item',before,after)
            return self._canonical(con,route_id)

    def remove_item(self, route_id, item_id, expected_revision=None):
        with self.db.transaction() as con:
            route_id, item_id, rev = self._prepare_edit(con, route_id, expected_revision, item_id)
            before=self._state(con,route_id)
            cur=con.execute('delete from route_items where route_id=? and id=?',(route_id,item_id))
            if cur.rowcount!=1: raise RouteItemNotFound(item_id)
            self._normalize_positions(con,route_id)
            after=self._state(con,route_id); self._record(con,route_id,rev,'remove_item',before,after)
            return self._canonical(con,route_id)

    def update_item(self, route_id, item_id, patch, expected_revision=None):
        allowed={'place_id','temporary_x','temporary_y','temporary_z','nav_anchor_point_id','scenic_block_id','direction','stop_type','position_locked','direction_locked','custom_label','type'}
        patch={k:v for k,v in patch.items() if k in allowed}
        with self.db.transaction() as con:
            route_id, item_id, rev = self._prepare_edit(con, route_id, expected_revision, item_id)
            before=self._state(con,route_id)
            row=con.execute('select * from route_items where route_id=? and id=?',(route_id,item_id)).fetchone()
            if not row: raise RouteItemNotFound(item_id)
            if patch:
                cols=[]; vals=[]
                for k,v in patch.items():
                    cols.append(f'{k}=?'); vals.append(1 if k in ('position_locked','direction_locked') and v else 0 if k in ('position_locked','direction_locked') else v)
                vals.extend([route_id,item_id]); con.execute(f"update route_items set {','.join(cols)} where route_id=? and id=?",vals)
            after=self._state(con,route_id); self._record(con,route_id,rev,'update_item',before,after)
            return self._canonical(con,route_id)

    def reverse_route(self, route_id, expected_revision=None, policy='cancel'):
        with self.db.transaction() as con:
            route_id, _, rev = self._prepare_edit(con, route_id, expected_revision)
            before=self._state(con,route_id)
            items=[dict(x) for x in reversed(before['items'])]
            for it in items:
                if it.get('type') not in ('scenic_road','scenic_loop'): continue
                if it.get('direction_locked'):
                    if policy=='cancel': raise RouteReverseConflict(f"direction locked for {it.get('id')}")
                    if policy=='keep': continue
                    if policy=='unlock': it['direction_locked']=False
                    else: raise ValueError('unknown reverse policy')
                if it.get('type')=='scenic_loop':
                    it['direction']='counterclockwise' if it.get('direction') in (None,'clockwise','cw','forward') else 'clockwise'
                else:
                    it['direction']='reverse' if it.get('direction') in (None,'forward') else 'forward'
            after={'name':before['name'],'is_draft':before['is_draft'],'items':items}
            self._replace_state(con,route_id,after); self._record(con,route_id,rev,'reverse',before,after)
            return self._canonical(con,route_id)

    def optimize_route(self, route_id, expected_revision=None, objective='fastest', keep_final=True, choose_orientation=True, start_anchor=None):
        if self.preview_service is None: raise ValueError('route preview service is not configured')
        from route_optimizer import optimize_items
        with self.db.transaction() as con:
            route_id, _, rev = self._prepare_edit(con, route_id, expected_revision)
            before=self._state(con,route_id)
            items=optimize_items(before['items'],self.preview_service,start_anchor=start_anchor,objective=objective,keep_final=keep_final,choose_orientation=choose_orientation)
            after={'name':before['name'],'is_draft':before['is_draft'],'items':items}
            self._replace_state(con,route_id,after); self._record(con,route_id,rev,'optimize',before,after)
            return self._canonical(con,route_id)

    def undo(self, route_id, expected_revision=None):
        if self._is_builtin(route_id):
            actual = int(self.builtin_routes.get(route_id)['revision'])
            if expected_revision is not None and int(expected_revision) != actual:
                raise RouteRevisionConflict(int(expected_revision), actual)
            return self.builtin_routes.get(route_id)
        with self.db.transaction() as con:
            rev=self._assert_revision(con,route_id,expected_revision)
            target=con.execute("select * from route_revisions where route_id=? and action not in ('undo','redo') and is_undone=0 order by id desc limit 1",(route_id,)).fetchone()
            if not target: return self._canonical(con,route_id)
            current=self._state(con,route_id); desired=json.loads(target['before_json'])
            self._replace_state(con,route_id,desired); con.execute('update route_revisions set is_undone=1 where id=?',(target['id'],))
            after=self._state(con,route_id); self._record(con,route_id,rev,'undo',current,after,clear_redo=False)
            return self._canonical(con,route_id)

    def redo(self, route_id, expected_revision=None):
        if self._is_builtin(route_id):
            actual = int(self.builtin_routes.get(route_id)['revision'])
            if expected_revision is not None and int(expected_revision) != actual:
                raise RouteRevisionConflict(int(expected_revision), actual)
            return self.builtin_routes.get(route_id)
        with self.db.transaction() as con:
            rev=self._assert_revision(con,route_id,expected_revision)
            target=con.execute("select * from route_revisions where route_id=? and action not in ('undo','redo') and is_undone=1 order by id asc limit 1",(route_id,)).fetchone()
            if not target: return self._canonical(con,route_id)
            current=self._state(con,route_id); desired=json.loads(target['after_json'])
            self._replace_state(con,route_id,desired); con.execute('update route_revisions set is_undone=0 where id=?',(target['id'],))
            after=self._state(con,route_id); self._record(con,route_id,rev,'redo',current,after,clear_redo=False)
            return self._canonical(con,route_id)
