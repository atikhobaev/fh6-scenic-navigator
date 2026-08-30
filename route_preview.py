from __future__ import annotations

from dataclasses import dataclass
import gzip
import heapq
import json
from pathlib import Path


@dataclass(frozen=True)
class Segment:
    id:int; section_id:int; from_point:int; to_point:int; length_m:float; oneway:bool; road_type:str


class DirectedGraph:
    def __init__(self,payload):
        caps=payload.get('capabilities') or {}
        if payload.get('format')!='fh6-navgraph-v1' or not caps.get('directed_segments') or not caps.get('turn_transitions'):
            raise ValueError('authoritative directed graph capabilities required')
        self.payload=payload
        self.points={int(p[0]):(float(p[1]),float(p[2]),float(p[3])) for p in payload.get('points',[])}
        self.segments={int(s[0]):Segment(int(s[0]),int(s[1]),int(s[2]),int(s[3]),float(s[4]),bool(s[5]),str(s[6] if len(s)>6 else 'unknown')) for s in payload.get('segments',[])}
        self.outgoing_by_point={}
        for s in self.segments.values(): self.outgoing_by_point.setdefault(s.from_point,[]).append(s.id)
        self.next_segments={}
        for a,b in payload.get('transitions',[]): self.next_segments.setdefault(int(a),[]).append(int(b))
        self.direct={}
        for s in self.segments.values(): self.direct.setdefault((s.from_point,s.to_point),[]).append(s.id)
        self._cache={}

    @classmethod
    def from_payload(cls,payload): return cls(payload)
    @classmethod
    def from_gzip_path(cls,path:Path): return cls(json.loads(gzip.decompress(Path(path).read_bytes()).decode('utf-8')))

    def direct_segment(self,a,b):
        ids=self.direct.get((int(a),int(b))) or []
        if not ids:return None
        return min((self.segments[i] for i in ids),key=lambda s:(s.length_m,s.id))

    def route_between(self,start_point,goal_point,objective='shortest'):
        start_point=int(start_point); goal_point=int(goal_point)
        if start_point==goal_point:return {'segment_ids':[],'point_ids':[start_point],'distance_m':0.0,'cost':0.0}
        key=(start_point,goal_point,objective)
        if key in self._cache:return self._cache[key]
        starts=self.outgoing_by_point.get(start_point,[])
        if not starts:self._cache[key]=None;return None
        def weight(seg):
            base=seg.length_m
            if objective=='fastest' and seg.road_type not in ('asphalt','road','paved'): base*=1.18
            return base
        heap=[]; dist={}; prev={}
        for sid in starts:
            s=self.segments[sid]; d=weight(s); dist[sid]=d; heapq.heappush(heap,(d,sid))
        end=None
        while heap:
            d,sid=heapq.heappop(heap)
            if d!=dist.get(sid):continue
            s=self.segments[sid]
            if s.to_point==goal_point: end=sid; break
            for nid in self.next_segments.get(sid,[]):
                ns=self.segments.get(nid)
                if ns is None or ns.from_point!=s.to_point: continue
                nd=d+weight(ns)
                if nd<dist.get(nid,float('inf')):
                    dist[nid]=nd; prev[nid]=sid; heapq.heappush(heap,(nd,nid))
        if end is None:self._cache[key]=None;return None
        ids=[]; cur=end
        while True:
            ids.append(cur)
            if cur not in prev:break
            cur=prev[cur]
        ids.reverse(); segs=[self.segments[i] for i in ids]
        point_ids=[start_point]+[s.to_point for s in segs]
        result={'segment_ids':ids,'point_ids':point_ids,'distance_m':round(sum(s.length_m for s in segs),3),'cost':dist[end]}
        self._cache[key]=result; return result

    def geometry(self,point_ids):
        return [[pid,*self.points[pid]] for pid in point_ids if pid in self.points]


def validate_scenic_block_definition(block):
    typ=block.get('type')
    if typ not in ('road','loop'): raise ValueError('unsupported scenic block type')
    if typ=='road':
        f=block.get('forward_anchor_point_ids') or []
        if len(f)<2: raise ValueError('scenic road forward path needs at least two anchors')
        if block.get('reversible') and len(block.get('reverse_anchor_point_ids') or [])<2: raise ValueError('reversible scenic road requires reverse path')
    else:
        cw=block.get('clockwise_anchor_point_ids') or []
        if len(cw)<2: raise ValueError('scenic loop clockwise path needs anchors')
        if block.get('reversible') and len(block.get('counterclockwise_anchor_point_ids') or [])<2: raise ValueError('reversible scenic loop requires counterclockwise path')
    return True


class RoutePreviewService:
    def __init__(self,graph:DirectedGraph,places=None): self.graph=graph; self.places=places

    def _anchor_for_item(self,item):
        if item.get('nav_anchor_point_id') is not None:return int(item['nav_anchor_point_id'])
        if item.get('place_id') and self.places is not None:
            p=self.places.get_place(item['place_id']); a=(p.get('navigation') or {}).get('anchor_point_id')
            return None if a is None else int(a)
        return None

    def _fixed_scenic(self,block,direction):
        validate_scenic_block_definition(block)
        if block['type']=='road':
            anchors=block.get('reverse_anchor_point_ids') if direction=='reverse' else block.get('forward_anchor_point_ids')
        else:
            anchors=block.get('counterclockwise_anchor_point_ids') if direction in ('counterclockwise','ccw','reverse') else block.get('clockwise_anchor_point_ids')
        anchors=[int(x) for x in anchors or []]
        ids=[]; distance=0.0
        for a,b in zip(anchors,anchors[1:]):
            seg=self.graph.direct_segment(a,b)
            if seg is None:return None
            ids.append(seg.id); distance+=seg.length_m
        return {'entry':anchors[0],'exit':anchors[-1],'segment_ids':ids,'point_ids':anchors,'distance_m':round(distance,3)}

    def _ordinary_leg(self,a,b,objective):
        r=self.graph.route_between(a,b,objective)
        if r is None:return {'resolved':False,'from_anchor':a,'to_anchor':b,'reason':'NO_LEGAL_DIRECTED_PATH','segment_ids':[],'point_ids':[],'distance_m':None}
        return {'resolved':True,'from_anchor':a,'to_anchor':b,'reason':None,**r}

    def item_anchor(self,item,direction=None):
        typ=item.get('type')
        if typ in ('scenic_road','scenic_loop'):
            if self.places is None: raise KeyError(item.get('scenic_block_id'))
            block=self.places.get_scenic_block(item['scenic_block_id'])
            fixed=self._fixed_scenic(block,direction or item.get('direction') or ('clockwise' if typ=='scenic_loop' else 'forward'))
            if fixed is None: raise ValueError('invalid scenic block path')
            return fixed['entry'],fixed['exit'],fixed['distance_m']
        anchor=self._anchor_for_item(item)
        if anchor is None: raise ValueError('missing anchor')
        return anchor,anchor,0.0

    def travel_cost(self,a,b,objective='fastest'):
        r=self.graph.route_between(a,b,objective)
        return None if r is None else float(r['cost'] if objective=='fastest' else r['distance_m'])

    def validate_items(self,items,start_anchor=None,objective='fastest'):
        current=start_anchor; total=0.0
        for item in items:
            try: entry,exit_,internal=self.item_anchor(item,item.get('direction'))
            except (KeyError,ValueError): return None
            if current is not None:
                cost=self.travel_cost(current,entry,objective)
                if cost is None:return None
                total+=float(cost)
            total+=float(internal or 0); current=exit_
        return total

    def preview(self,route,start_anchor=None,objective='shortest'):
        items=list(route.get('items') or []); legs=[]; all_points=[]; total=0.0; resolved=True; current=None if start_anchor is None else int(start_anchor)
        index=0
        if current is None and items:
            first=items[0]
            if first.get('type') in ('scenic_road','scenic_loop'):
                block=self.places.get_scenic_block(first['scenic_block_id']) if self.places else None
                if block:
                    fixed=self._fixed_scenic(block,first.get('direction') or ('clockwise' if block.get('type')=='loop' else 'forward'))
                    current=fixed['entry'] if fixed else None
                else: current=None
            else: current=self._anchor_for_item(first)
            index=1
        for item in items[index:]:
            typ=item.get('type')
            if typ in ('scenic_road','scenic_loop'):
                try: block=self.places.get_scenic_block(item['scenic_block_id']) if self.places else None
                except KeyError: block=None
                if not block:
                    legs.append({'item_id':item.get('id'),'resolved':False,'reason':'UNKNOWN_SCENIC_BLOCK','segment_ids':[],'point_ids':[],'distance_m':None}); resolved=False; current=None; continue
                fixed=self._fixed_scenic(block,item.get('direction') or ('clockwise' if block.get('type')=='loop' else 'forward'))
                if fixed is None:
                    legs.append({'item_id':item.get('id'),'resolved':False,'reason':'INVALID_SCENIC_BLOCK_PATH','segment_ids':[],'point_ids':[],'distance_m':None}); resolved=False; current=None; continue
                approach={'resolved':True,'segment_ids':[],'point_ids':[fixed['entry']],'distance_m':0.0}
                if current is not None and current!=fixed['entry']:
                    approach=self._ordinary_leg(current,fixed['entry'],objective)
                if not approach['resolved']:
                    legs.append({'item_id':item.get('id'),**approach,'scenic_distance_m':fixed['distance_m']}); resolved=False; current=None; continue
                segs=list(approach['segment_ids'])+list(fixed['segment_ids'])
                pts=list(approach['point_ids'])
                if pts and fixed['point_ids'] and pts[-1]==fixed['point_ids'][0]: pts+=fixed['point_ids'][1:]
                else: pts+=fixed['point_ids']
                dist=float(approach['distance_m'])+fixed['distance_m']; total+=dist
                legs.append({'item_id':item.get('id'),'resolved':True,'reason':None,'from_anchor':current,'to_anchor':fixed['exit'],'segment_ids':segs,'point_ids':pts,'distance_m':round(dist,3),'approach_distance_m':approach['distance_m'],'scenic_distance_m':fixed['distance_m'],'block_id':block['id']})
                current=fixed['exit']; all_points += pts if not all_points else pts[1:]
            else:
                target=self._anchor_for_item(item)
                if current is None or target is None:
                    legs.append({'item_id':item.get('id'),'resolved':False,'reason':'MISSING_NAV_ANCHOR','segment_ids':[],'point_ids':[],'distance_m':None}); resolved=False; current=target; continue
                leg=self._ordinary_leg(current,target,objective); leg['item_id']=item.get('id'); legs.append(leg)
                if leg['resolved']:
                    total+=float(leg['distance_m']); all_points += leg['point_ids'] if not all_points else leg['point_ids'][1:]
                else: resolved=False
                current=target
        return {'format':'fh6-route-preview-v1','route_id':route.get('id'),'revision':int(route.get('revision',0)),'resolved':resolved,'total_distance_m':round(total,3) if resolved or total else 0.0,'legs':legs,'point_ids':all_points,'geometry':self.graph.geometry(all_points)}
