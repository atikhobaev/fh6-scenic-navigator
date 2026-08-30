from __future__ import annotations
import gzip,json
from pathlib import Path
from .graph import Graph


def compile_graph_dict(graph:Graph):
    return {
        'format':'fh6-navgraph-v1',
        'source':{'sha256':graph.source_sha256,'size_bytes':graph.source_size,'signature':'WVAN'},
        'capabilities':graph.capabilities,
        'stats':{**graph.stats,'points':len(graph.points),'segments':len(graph.segments),'transitions':len(graph.transitions)},
        'points':[[p.id,round(p.x,5),round(p.y,5),round(p.z,5)] for p in graph.points],
        'segments':[[s.id,s.section_id,s.from_point,s.to_point,round(s.length,3),1 if s.oneway else 0,s.road_type or ''] for s in graph.segments],
        'transitions':[[a,b] for a,b in graph.transitions],
    }

def write_graph(graph:Graph,path):
    p=Path(path); payload=compile_graph_dict(graph)
    raw=json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode('utf-8')
    if p.suffix=='.gz': p.write_bytes(gzip.compress(raw,compresslevel=9))
    else: p.write_bytes(raw)
    return p
