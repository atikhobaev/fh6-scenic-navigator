from __future__ import annotations

import gzip
import json
import math
from pathlib import Path
import uuid

from planner_database import PlannerDatabase, utc_now


class CatalogValidationError(ValueError): pass


REQUIRED_PLACE_KEYS={'id','source','kind','name','category','position','navigation','default_visible','featured','quality'}


class PlacesService:
    def __init__(self,builtin_path:Path,curated_path:Path,db:PlannerDatabase,navgraph_path:Path|None=None,community_path:Path|None=None,media_root:Path|None=None):
        self.builtin_path=Path(builtin_path); self.curated_path=Path(curated_path); self.db=db
        self.navgraph_path=Path(navgraph_path) if navgraph_path else None
        self.community_path=Path(community_path) if community_path else None
        self.media_root=Path(media_root) if media_root else None
        self._graph_points=None
        self._builtin=self._load_catalog(self.builtin_path,'game')
        self._curated_doc=self._load_doc(self.curated_path)
        self._curated=self._validate_places(self._curated_doc.get('places',[]),'curated')
        self._community_doc=self._load_doc(self.community_path) if self.community_path else {'schema_version':1,'catalog_version':None,'places':[]}
        self._community=self._validate_places(self._community_doc.get('places',[]),'community')
        ids=[p['id'] for p in self._builtin+self._curated+self._community]
        if len(ids)!=len(set(ids)): raise CatalogValidationError('duplicate stable place id across catalogs')
        self._static={p['id']:p for p in self._builtin+self._curated+self._community}

    def _load_doc(self,path):
        try: doc=json.loads(path.read_text(encoding='utf-8'))
        except (OSError,json.JSONDecodeError) as e: raise CatalogValidationError(f'{path}: {e}')
        if doc.get('schema_version')!=1: raise CatalogValidationError(f'{path}: unsupported schema_version')
        return doc

    def _load_catalog(self,path,expected_source):
        doc=self._load_doc(path)
        return self._validate_places(doc.get('places',[]),expected_source)

    def _validate_places(self,places,expected_source):
        if not isinstance(places,list): raise CatalogValidationError('places must be a list')
        out=[]; ids=set()
        for raw in places:
            if not isinstance(raw,dict) or not REQUIRED_PLACE_KEYS.issubset(raw): raise CatalogValidationError('malformed place record')
            p=dict(raw)
            if p['id'] in ids: raise CatalogValidationError(f'duplicate place id {p["id"]}')
            ids.add(p['id'])
            if expected_source and p.get('source')!=expected_source: raise CatalogValidationError(f'{p["id"]}: wrong source')
            pos=p.get('position') or {}
            if not all(isinstance(pos.get(k),(int,float)) and math.isfinite(float(pos[k])) for k in ('x','y','z')): raise CatalogValidationError(f'{p["id"]}: invalid position')
            for image_key in ('image','image_thumb'):
                image=p.get(image_key)
                if image is not None:
                    self._validate_local_image(p['id'],image_key,image)
            p.setdefault('aliases',[]); p.setdefault('subcategory',''); p.setdefault('tags',[]); p.setdefault('surface','unknown'); p.setdefault('access','normal'); p.setdefault('scenic_score',0)
            out.append(p)
        return out

    def _validate_local_image(self,place_id,key,value):
        if not isinstance(value,str) or not value.startswith('/media/places/') or '://' in value:
            raise CatalogValidationError(f'{place_id}: {key} must be a local /media/places path')
        rel=value[len('/media/places/'):]
        rel_path=Path(rel)
        if not rel or rel_path.is_absolute() or '..' in rel_path.parts:
            raise CatalogValidationError(f'{place_id}: invalid {key} path')
        if self.media_root is not None:
            candidate=(self.media_root/rel_path).resolve()
            root=self.media_root.resolve()
            if root not in candidate.parents or not candidate.is_file():
                raise CatalogValidationError(f'{place_id}: missing local {key} asset {value}')

    def _favorites(self):
        with self.db.connect() as con: return {r['place_id'] for r in con.execute('select place_id from favorites')}

    def _user_places(self):
        fav=self._favorites()
        with self.db.connect() as con: rows=con.execute('select * from user_places order by updated_at desc').fetchall()
        out=[]
        for r in rows:
            out.append({'id':r['id'],'source':'user','kind':'point','name':r['name'],'aliases':[],'category':r['category'],'subcategory':'','tags':[],'position':{'x':r['x'],'y':r['y'],'z':r['z']},'navigation':{'anchor_point_id':r['nav_anchor_point_id'],'snap_distance_m':r['nav_snap_distance']},'surface':'unknown','access':'normal','scenic_score':0,'default_visible':True,'featured':False,'quality':'verified','notes':r['notes'],'favorite':r['id'] in fav})
        return out

    def list_places(self,mode='recommended'):
        fav=self._favorites(); items=[]
        for p in self._builtin+self._curated+self._community:
            if mode=='recommended' and not p.get('default_visible'): continue
            q=dict(p); q['favorite']=q['id'] in fav; items.append(q)
        items.extend(self._user_places())
        return items

    def get_place(self,place_id):
        fav=self._favorites()
        if place_id in self._static:
            p=dict(self._static[place_id]); p['favorite']=place_id in fav; return p
        with self.db.connect() as con: r=con.execute('select * from user_places where id=?',(place_id,)).fetchone()
        if not r: raise KeyError(place_id)
        return next(p for p in self._user_places() if p['id']==place_id)

    def catalog_info(self):
        allp=self.list_places('all'); rec=self.list_places('recommended')
        return {
            'total':len(allp),'recommended':len(rec),
            'builtin_version':self._load_doc(self.builtin_path).get('catalog_version'),
            'curated_version':self._curated_doc.get('catalog_version'),
            'community_version':self._community_doc.get('catalog_version'),
        }

    def set_favorite(self,place_id,enabled=True):
        self.get_place(place_id)
        with self.db.transaction() as con:
            if enabled: con.execute('insert into favorites(place_id,created_at) values(?,?) on conflict(place_id) do nothing',(place_id,utc_now()))
            else: con.execute('delete from favorites where place_id=?',(place_id,))
        return self.get_place(place_id)

    def _load_graph_points(self):
        if self._graph_points is not None: return self._graph_points
        if not self.navgraph_path or not self.navgraph_path.is_file(): self._graph_points=[]; return self._graph_points
        doc=json.loads(gzip.decompress(self.navgraph_path.read_bytes()).decode('utf-8'))
        if doc.get('format')!='fh6-navgraph-v1': raise CatalogValidationError('invalid navgraph format')
        self._graph_points=[(int(p[0]),float(p[1]),float(p[2]),float(p[3])) for p in doc.get('points',[])]
        return self._graph_points

    def snap(self,x,y,z):
        pts=self._load_graph_points()
        if not pts: return None,None
        best=min(pts,key=lambda p:(p[1]-x)**2+(p[3]-z)**2)
        dist=math.hypot(best[1]-x,best[3]-z)
        return best[0],dist

    def create_user_place(self,data):
        name=(data.get('name') or '').strip()
        if not name: raise ValueError('name is required')
        x=float(data['x']); y=float(data.get('y',0)); z=float(data['z'])
        anchor,dist=self.snap(x,y,z); pid=f'user.{uuid.uuid4()}' ; now=utc_now()
        with self.db.transaction() as con:
            con.execute('insert into user_places(id,name,category,notes,x,y,z,nav_anchor_point_id,nav_snap_distance,created_at,updated_at) values(?,?,?,?,?,?,?,?,?,?,?)',(pid,name,data.get('category') or 'my_place',data.get('notes') or '',x,y,z,anchor,dist,now,now))
        return self.get_place(pid)

    def update_user_place(self,place_id,patch):
        with self.db.transaction() as con:
            r=con.execute('select * from user_places where id=?',(place_id,)).fetchone()
            if not r: raise KeyError(place_id)
            name=(patch.get('name',r['name']) or '').strip(); x=float(patch.get('x',r['x'])); y=float(patch.get('y',r['y'])); z=float(patch.get('z',r['z']))
            anchor,dist=self.snap(x,y,z)
            con.execute('update user_places set name=?,category=?,notes=?,x=?,y=?,z=?,nav_anchor_point_id=?,nav_snap_distance=?,updated_at=? where id=?',(name,patch.get('category',r['category']),patch.get('notes',r['notes']),x,y,z,anchor,dist,utc_now(),place_id))
        return self.get_place(place_id)

    def delete_user_place(self,place_id,force=False):
        with self.db.transaction() as con:
            r=con.execute('select id from user_places where id=?',(place_id,)).fetchone()
            if not r: raise KeyError(place_id)
            refs=con.execute('select count(*) from route_items where place_id=?',(place_id,)).fetchone()[0]
            if refs and not force: raise ValueError(f'place is used by {refs} route items')
            if force: con.execute('update route_items set place_id=null where place_id=?',(place_id,))
            con.execute('delete from favorites where place_id=?',(place_id,)); con.execute('delete from user_places where id=?',(place_id,))
        return {'deleted':place_id,'references':refs}

    def get_scenic_block(self, block_id):
        for block in self._curated_doc.get('blocks',[]):
            if block.get('id') == block_id:
                return dict(block)
        raise KeyError(block_id)

    @property
    def scenic_blocks(self): return list(self._curated_doc.get('blocks',[]))
    @property
    def collections(self): return list(self._curated_doc.get('collections',[]))
