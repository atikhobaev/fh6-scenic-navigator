from __future__ import annotations

import uuid
from planner_database import utc_now

BACKUP_FORMAT='fh6-navigator-backup'
ROUTE_FORMAT='fh6route'
FORMAT_VERSION=1


class PlannerIO:
    def __init__(self, db, routes, places):
        self.db=db; self.routes=routes; self.places=places

    def _user_places(self):
        with self.db.connect() as con:
            return [dict(r) for r in con.execute('select * from user_places order by created_at,id').fetchall()]

    def _favorites(self):
        with self.db.connect() as con:
            return [r['place_id'] for r in con.execute('select place_id from favorites order by place_id').fetchall()]

    def export_backup(self):
        return {
            'format':BACKUP_FORMAT,'format_version':FORMAT_VERSION,'created_at':utc_now(),
            'user_places':self._user_places(),'favorites':self._favorites(),
            'routes':self.routes.list_routes(),
            'app_state':{'active_route_id':self.db.get_app_state().get('active_route_id')},
        }

    def export_route(self, route_id):
        route=self.routes.get_route(route_id)
        refs={i.get('place_id') for i in route.get('items',[]) if i.get('place_id','').startswith('user.')}
        user=[p for p in self._user_places() if p['id'] in refs]
        return {'format':ROUTE_FORMAT,'format_version':FORMAT_VERSION,'created_at':utc_now(),'route':route,'user_places':user}

    @staticmethod
    def _validate(doc, expected):
        if not isinstance(doc,dict) or doc.get('format')!=expected: raise ValueError(f'unsupported {expected} document')
        if int(doc.get('format_version',0))!=FORMAT_VERSION: raise ValueError(f'unsupported format version {doc.get("format_version")}')

    def _import_user_places(self, rows):
        mapping={}
        now=utc_now()
        with self.db.transaction() as con:
            existing={r['id'] for r in con.execute('select id from user_places').fetchall()}
            for raw in rows or []:
                old=str(raw.get('id') or f'user.{uuid.uuid4()}')
                new=old if old not in existing else f'user.{uuid.uuid4()}'
                existing.add(new); mapping[old]=new
                con.execute('insert into user_places(id,name,category,notes,x,y,z,nav_anchor_point_id,nav_snap_distance,created_at,updated_at) values(?,?,?,?,?,?,?,?,?,?,?)',(
                    new,str(raw.get('name') or 'Imported place'),str(raw.get('category') or 'my_place'),str(raw.get('notes') or ''),
                    float(raw.get('x',0)),float(raw.get('y',0)),float(raw.get('z',0)),raw.get('nav_anchor_point_id'),raw.get('nav_snap_distance'),now,now))
        return mapping

    def _resolve_warning(self, place_id, mapping):
        if not place_id:return None
        resolved=mapping.get(place_id,place_id)
        try:self.places.get_place(resolved);return None
        except KeyError:return f'unresolved place reference: {place_id}'

    def _import_route_record(self, raw, user_mapping):
        warnings=[]
        route=self.routes.create_route(str(raw.get('name') or 'Imported Route'),bool(raw.get('is_draft',False)),make_active=False)
        for item in raw.get('items') or []:
            q={k:v for k,v in dict(item).items() if k not in ('id','route_id','position')}
            if q.get('place_id') in user_mapping:q['place_id']=user_mapping[q['place_id']]
            w=self._resolve_warning(q.get('place_id'),user_mapping)
            if w:warnings.append(w)
            try:
                route=self.routes.add_item(route['id'],q,route['revision'])
            except Exception:
                # Preserve unresolved references in imported data rather than deleting the rest of the import.
                route=self.routes.add_item(route['id'],q,route['revision'])
        return route,warnings

    def import_route(self, doc):
        self._validate(doc,ROUTE_FORMAT)
        mapping=self._import_user_places(doc.get('user_places') or [])
        route,warnings=self._import_route_record(doc.get('route') or {},mapping)
        return {'route':route,'warnings':warnings,'user_place_id_map':mapping}

    def import_backup(self, doc):
        self._validate(doc,BACKUP_FORMAT)
        mapping=self._import_user_places(doc.get('user_places') or [])
        imported=[]; warnings=[]
        for raw in doc.get('routes') or []:
            r,w=self._import_route_record(raw,mapping); imported.append(r['id']); warnings.extend(w)
        with self.db.transaction() as con:
            for old in doc.get('favorites') or []:
                pid=mapping.get(old,old)
                try:self.places.get_place(pid)
                except KeyError:
                    warnings.append(f'unresolved favorite reference: {old}'); continue
                con.execute('insert into favorites(place_id,created_at) values(?,?) on conflict(place_id) do nothing',(pid,utc_now()))
        return {'imported_route_ids':imported,'warnings':warnings,'user_place_id_map':mapping}
