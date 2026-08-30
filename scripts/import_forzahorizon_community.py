from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path
import urllib.request


CATEGORY_MAP = {
    'scenic': 'scenic_spot',
    'scenic spot': 'scenic_spot',
    'secret road': 'secret_road',
    'jump': 'jump',
    'easter egg': 'easter_egg',
    'collectible': 'collectible',
    'barn find': 'barn_find',
    'other': 'other',
}


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _source_key(record):
    value=str(record.get('source_id') or '').strip()
    if value:return value
    seed='|'.join([str(record.get('source_url') or ''),str(record.get('title') or '')])
    return 'evidence-' + hashlib.sha256(seed.encode('utf-8')).hexdigest()[:16]


def normalize_record(raw):
    source_id=str(raw.get('source_id') or '').strip() or None
    title=str(raw.get('title') or raw.get('name') or '').strip()
    if not title: raise ValueError('community record title is required')
    category=CATEGORY_MAP.get(str(raw.get('category') or 'other').strip().casefold(),'other')
    return {
        'source_provider':'forzahorizon.app',
        'source_id':source_id,
        'source_key':_source_key(raw),
        'title':title,
        'category':category,
        'contributor':raw.get('contributor'),
        'likes':int(raw.get('likes') or 0),
        'source_url':raw.get('source_url'),
        'screenshot_url':raw.get('screenshot_url'),
        'approved_at':raw.get('approved_at'),
    }


def deterministic_image_name(source_key, content_type='image/jpeg'):
    ext={
        'image/jpeg':'.jpg','image/jpg':'.jpg','image/png':'.png','image/webp':'.webp','image/avif':'.avif',
    }.get(str(content_type or '').split(';',1)[0].strip().lower(),'.img')
    digest=hashlib.sha256(str(source_key).encode('utf-8')).hexdigest()[:20]
    return f'forzahorizon_{digest}{ext}'


def compile_records(records, *, coordinates, snapper, media_dir=None, fetcher=None, fetched_at=None):
    runtime=[]; evidence=[]; fetched_at=fetched_at or _now()
    media_dir=Path(media_dir) if media_dir is not None else None
    if media_dir is not None: media_dir.mkdir(parents=True,exist_ok=True)
    for raw in records or []:
        src=normalize_record(raw); source_key=src['source_key']
        ev=dict(src); ev['fetched_at']=fetched_at
        pos=(coordinates or {}).get(source_key)
        if pos is None and src.get('source_id'):
            pos=(coordinates or {}).get(src['source_id'])
        if pos is None:
            ev.update(release_status='evidence_only',release_reason='missing_proven_coordinates'); evidence.append(ev); continue
        try:
            x=float(pos['x']); y=float(pos.get('y',0)); z=float(pos['z'])
            if not all(math.isfinite(v) for v in (x,y,z)): raise ValueError
        except (KeyError,TypeError,ValueError):
            ev.update(release_status='evidence_only',release_reason='invalid_proven_coordinates'); evidence.append(ev); continue
        anchor,dist=snapper(x,y,z)
        if anchor is None:
            ev.update(release_status='evidence_only',release_reason='no_wvan_anchor',position={'x':x,'y':y,'z':z}); evidence.append(ev); continue
        image_path=None; attribution=None
        if src.get('screenshot_url') and media_dir is not None and fetcher is not None:
            payload,ctype=fetcher(src['screenshot_url'])
            if not isinstance(payload,(bytes,bytearray)) or not payload: raise ValueError(f'{source_key}: empty screenshot')
            name=deterministic_image_name(source_key,ctype); (media_dir/name).write_bytes(bytes(payload))
            checksum=hashlib.sha256(bytes(payload)).hexdigest()
            image_path='/media/places/community/'+name
            attribution={
                'provider':'forzahorizon.app','contributor':src.get('contributor'),'source_url':src.get('source_url'),
                'checksum_sha256':checksum,'fetched_at':fetched_at,
            }
        pid='community.forzahorizon.'+hashlib.sha256(source_key.encode('utf-8')).hexdigest()[:20]
        row={
            'id':pid,'source':'community','kind':'point','name':src['title'],'aliases':[],
            'category':src['category'],'subcategory':'forzahorizon','tags':['community','forzahorizon.app'],
            'position':{'x':x,'y':y,'z':z},
            'navigation':{'anchor_point_id':int(anchor),'snap_distance_m':float(dist)},
            'surface':'unknown','access':'normal','scenic_score':0,'default_visible':False,'featured':False,'quality':'verified',
            'image_source':'forzahorizon.app','external_source_id':src.get('source_id'),'popularity':src.get('likes',0),
            'source_metadata':{'source_url':src.get('source_url'),'contributor':src.get('contributor'),'approved_at':src.get('approved_at')},
        }
        if image_path:
            row['image']=image_path; row['image_attribution']=attribution
        runtime.append(row)
        ev.update(release_status='runtime',release_reason=None,position=row['position'],nav_anchor_point_id=int(anchor),nav_snap_distance_m=float(dist),local_image=image_path)
        evidence.append(ev)
    return runtime,evidence


def graph_snapper(navgraph_path):
    payload=json.loads(gzip.decompress(Path(navgraph_path).read_bytes()).decode('utf-8'))
    if payload.get('format')!='fh6-navgraph-v1': raise ValueError('invalid navgraph format')
    pts=[(int(p[0]),float(p[1]),float(p[2]),float(p[3])) for p in payload.get('points',[])]
    def snap(x,y,z):
        if not pts:return None,None
        best=min(pts,key=lambda p:(p[1]-x)**2+(p[3]-z)**2)
        return best[0],math.hypot(best[1]-x,best[3]-z)
    return snap


def http_fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'FH6-Scenic-Navigator community importer'})
    with urllib.request.urlopen(req,timeout=20) as response:
        return response.read(),response.headers.get_content_type()


def main(argv=None):
    p=argparse.ArgumentParser(description='Compile ForzaHorizon.app evidence into an offline FH6 community catalog')
    p.add_argument('--evidence',type=Path,default=Path('static/data/community_evidence.json'))
    p.add_argument('--coordinates',type=Path,required=True,help='JSON mapping of source_id/source_key to proven FH6 world x/y/z')
    p.add_argument('--navgraph',type=Path,default=Path('static/data/fh6_navgraph_v1.json.gz'))
    p.add_argument('--output',type=Path,default=Path('static/data/community_places.json'))
    p.add_argument('--media-dir',type=Path,default=Path('static/media/places/community'))
    p.add_argument('--download-images',action='store_true')
    args=p.parse_args(argv)
    evidence_doc=json.loads(args.evidence.read_text(encoding='utf-8'))
    coordinates=json.loads(args.coordinates.read_text(encoding='utf-8'))
    runtime,evidence=compile_records(
        evidence_doc.get('records') or [],coordinates=coordinates,snapper=graph_snapper(args.navgraph),
        media_dir=args.media_dir,fetcher=http_fetch if args.download_images else None,
    )
    out={'schema_version':1,'catalog_version':datetime.now(timezone.utc).strftime('%Y-%m-%d'),'places':runtime}
    args.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'runtime_places':len(runtime),'evidence_records':len(evidence)},ensure_ascii=False))
    return 0


if __name__=='__main__': raise SystemExit(main())
