from __future__ import annotations
import math
from pathlib import Path

class CatalogValidationError(ValueError): pass


def _path_ok(path,edges):
    return isinstance(path,list) and len(path)>=2 and all((int(a),int(b)) in edges for a,b in zip(path,path[1:]))


def _validate_runtime_image(pid,key,value,media_root=None):
    if value is None:return
    if not isinstance(value,str) or not value.startswith('/media/places/') or '://' in value:
        raise CatalogValidationError(f'{pid}: {key} must be a local /media/places path')
    rel=Path(value[len('/media/places/'):])
    if not rel.parts or rel.is_absolute() or '..' in rel.parts:
        raise CatalogValidationError(f'{pid}: invalid {key} path')
    if media_root is not None and not (Path(media_root)/rel).is_file():
        raise CatalogValidationError(f'{pid}: missing local {key} asset {value}')


def validate_catalogs(builtin_doc, curated_doc, graph_payload, community_doc=None, media_root=None):
    if graph_payload.get('format')!='fh6-navgraph-v1': raise CatalogValidationError('invalid directed graph format')
    points={int(p[0]) for p in graph_payload.get('points',[])}
    edges={(int(s[2]),int(s[3])) for s in graph_payload.get('segments',[])}
    all_places=list(builtin_doc.get('places') or [])+list(curated_doc.get('places') or [])+list((community_doc or {}).get('places') or [])
    ids=set(); source_map=set()
    for p in all_places:
        pid=p.get('id')
        if not pid or pid in ids: raise CatalogValidationError(f'duplicate place id: {pid}')
        ids.add(pid)
        if not str(p.get('name') or '').strip(): raise CatalogValidationError(f'{pid}: missing name')
        if not str(p.get('category') or '').strip(): raise CatalogValidationError(f'{pid}: missing category')
        pos=p.get('position') or {}
        if not all(isinstance(pos.get(k),(int,float)) and math.isfinite(float(pos[k])) for k in ('x','y','z')):
            raise CatalogValidationError(f'{pid}: invalid coordinate')
        anchor=(p.get('navigation') or {}).get('anchor_point_id')
        if anchor is not None and int(anchor) not in points: raise CatalogValidationError(f'{pid}: broken navigation anchor {anchor}')
        _validate_runtime_image(pid,'image',p.get('image'),media_root)
        _validate_runtime_image(pid,'image_thumb',p.get('image_thumb'),media_root)
        for src in p.get('sources') or []:
            key=(src.get('provider'),src.get('source_id'))
            if not all(key):continue
            if key in source_map: raise CatalogValidationError(f'duplicate source mapping: {key[0]}:{key[1]}')
            source_map.add(key)
    block_ids=set()
    for b in curated_doc.get('blocks') or []:
        bid=b.get('id')
        if not bid or bid in block_ids or bid in ids: raise CatalogValidationError(f'duplicate scenic block id: {bid}')
        block_ids.add(bid); typ=b.get('type')
        if typ=='road':
            forward=b.get('forward_anchor_point_ids') or []
            if not _path_ok(forward,edges): raise CatalogValidationError(f'{bid}: broken scenic forward path')
            if b.get('reversible'):
                reverse=b.get('reverse_anchor_point_ids') or []
                if not _path_ok(reverse,edges): raise CatalogValidationError(f'{bid}: broken scenic reverse path')
        elif typ=='loop':
            clockwise=b.get('clockwise_anchor_point_ids') or []
            if not _path_ok(clockwise,edges): raise CatalogValidationError(f'{bid}: broken scenic clockwise path')
            if b.get('reversible'):
                counter=b.get('counterclockwise_anchor_point_ids') or []
                if not _path_ok(counter,edges): raise CatalogValidationError(f'{bid}: broken scenic reverse/counterclockwise path')
        else: raise CatalogValidationError(f'{bid}: unsupported scenic block type')
    known=ids|block_ids
    for c in curated_doc.get('collections') or []:
        for ref in c.get('items') or c.get('place_ids') or []:
            rid=ref if isinstance(ref,str) else ref.get('id')
            if rid and rid not in known: raise CatalogValidationError(f'{c.get("id")}: broken collection reference {rid}')
    return {'valid':True,'places':len(all_places),'blocks':len(block_ids),'collections':len(curated_doc.get('collections') or []),'graph_points':len(points),'graph_edges':len(edges)}


def runtime_diagnostics(places_service, navgraph_path):
    import gzip,json
    graph=json.loads(gzip.decompress(Path(navgraph_path).read_bytes()).decode('utf-8'))
    builtin=places_service._load_doc(places_service.builtin_path)
    curated=places_service._curated_doc
    community=places_service._community_doc
    report=validate_catalogs(builtin,curated,graph,community_doc=community,media_root=places_service.media_root)
    report['catalog']=places_service.catalog_info()
    report['navgraph']={'format':graph.get('format'),'capabilities':graph.get('capabilities') or {},'source':graph.get('source') or {},'stats':graph.get('stats') or {}}
    return report
