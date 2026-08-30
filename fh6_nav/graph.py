from __future__ import annotations
from dataclasses import dataclass
import math
from .wvan import WvanDocument

KNOWN_VALIDATED_SHA='f06b4b958e60af5e52bc456173a5ba2b3ce6c900c732c8c5d96bd426498f5dbb'

@dataclass(frozen=True)
class Segment:
    id:int; section_id:int; from_point:int; to_point:int; length:float; oneway:bool; road_type:str|None; satnav:bool|None; tunnel:bool|None; layered:bool|None

@dataclass(frozen=True)
class Graph:
    source_sha256:str; source_size:int; points:tuple; segments:tuple[Segment,...]; transitions:tuple[tuple[int,int],...]; capabilities:dict; stats:dict


def _pairs(ent): return ent.values if ent else ()
def _last_value(ent,key):
    v=None
    for k,x in _pairs(ent):
        if k==key: v=x
    return v

def _true(ent,key): return _last_value(ent,key)=='true'

def _point_attrs(doc,pid): return doc.point_metadata.get(pid)
def _section_attrs(doc,sid): return doc.section_metadata.get(sid)

def _right_turn(a,b,c):
    v1=(b.x-a.x,b.z-a.z); v2=(c.x-b.x,c.z-b.z)
    return v1[0]*v2[1]-v1[1]*v2[0] < -1e-7


def build_graph(doc:WvanDocument)->Graph:
    segs=[]
    for sec in doc.sections:
        ids=doc.point_sequence[sec.sequence_start:sec.sequence_start+sec.sequence_count]
        sent=_section_attrs(doc,sec.id)
        road_type=_last_value(sent,'road_type')
        satnav=True if _true(sent,'satnav') else None
        tunnel=True if _true(sent,'is_tunnel') else None
        layered=True if _true(sent,'is_layered') else None
        for a,b in zip(ids,ids[1:]):
            if a==b: continue
            pa,pb=doc.points[a],doc.points[b]
            length=math.hypot(pb.x-pa.x,pb.z-pa.z)
            if length < 0.01: continue
            one=_true(sent,'oneway_forward') or _true(_point_attrs(doc,a),'oneway_forward') or _true(_point_attrs(doc,b),'oneway_forward')
            segs.append(Segment(len(segs),sec.id,a,b,length,one,road_type,satnav,tunnel,layered))
            if not one:
                segs.append(Segment(len(segs),sec.id,b,a,length,False,road_type,satnav,tunnel,layered))
    outgoing={}
    for s in segs: outgoing.setdefault(s.from_point,[]).append(s)
    transitions=[]; forbidden_uturn=0; forbidden_right=0
    for incoming in segs:
        junction=incoming.to_point
        pmeta=_point_attrs(doc,junction); smeta=_section_attrs(doc,incoming.section_id)
        no_right=_true(pmeta,'no_right_turn') or _true(smeta,'no_right_turn')
        for out in outgoing.get(junction,()):
            if out.to_point==incoming.from_point:
                forbidden_uturn+=1; continue
            if no_right and _right_turn(doc.points[incoming.from_point],doc.points[junction],doc.points[out.to_point]):
                forbidden_right+=1; continue
            transitions.append((incoming.id,out.id))
    caps={'geometry':True,'road_attributes':True,'directed_segments':True,'turn_transitions':True,'route_validated':doc.source_sha256==KNOWN_VALIDATED_SHA}
    stats={'forbidden_immediate_uturn':forbidden_uturn,'forbidden_no_right_turn':forbidden_right}
    return Graph(doc.source_sha256,doc.source_size,doc.points,tuple(segs),tuple(transitions),caps,stats)
