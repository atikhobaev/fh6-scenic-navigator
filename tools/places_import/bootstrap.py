from __future__ import annotations

import concurrent.futures
import gzip
import html as html_lib
import json
import math
import os
import re
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .build import load_navgraph
from .build_catalog import build_runtime_catalog
from .media import cache_image_bytes, extract_image_urls
from .models import RawPlace, SourceRef
from .normalize import normalize_text, stable_place_id
from .snap import NavGraphSnapper

MAPGENIE_URL='https://mapgenie.io/forza-horizon-6/maps/japan'
HUB_BASE='https://forzahorizonhub.com/map'
USER_AGENT='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36'

@dataclass(frozen=True)
class HubCategory:
    slug: str
    title: str
    count: int

HUB_CATEGORIES=(
    HubCategory('landmark','Landmark',75), HubCategory('player-house','Player House',8), HubCategory('car-meet','Car Meet',3), HubCategory('drag-meet','Drag Meet',3),
    HubCategory('day-trip','Day Trip',6), HubCategory('drift-club-japan','Drift Club Japan',1), HubCategory('moto-auto-zine','Moto Auto Zine',1), HubCategory('yujis-auto',"Yuji's Auto",1), HubCategory('food-delivery-job','Food Delivery Job',1),
    HubCategory('festival-site','Festival Site',2), HubCategory('horizon-event','Horizon Event',8),
    HubCategory('danger-sign','Danger Sign',20), HubCategory('drift-zone','Drift Zone',20), HubCategory('speed-trap','Speed Trap',30), HubCategory('trailblazer','Trailblazer Start Gate',11), HubCategory('speed-zone','Speed Zone',30),
    HubCategory('cross-country-event','Cross-Country Event',19), HubCategory('road-racing-event','Road Racing Event',22), HubCategory('street-racing-event','Street Racing Event',15), HubCategory('dirt-racing-event','Dirt Racing Event',21), HubCategory('touge-racing-event','Touge Racing Event',5), HubCategory('time-attack','Time Attack',4), HubCategory('drag-racing-event','Drag Racing Event',3),
    HubCategory('barn-find','Barn Find',15), HubCategory('treasure-car','Treasure Car',9), HubCategory('bonus-board','Bonus Board',200), HubCategory('aftermarket-car','Aftermarket Car',31), HubCategory('photo-location','Photo Location',21),
    HubCategory('curry','Curry Mascot',20), HubCategory('dango','Dango Mascot',25), HubCategory('edamame','Edamame Mascot',20), HubCategory('kakigori','Kakigori Mascot',20), HubCategory('matcha','Matcha Mascot',25), HubCategory('omurice','Omurice Mascot',15), HubCategory('onigiri','Onigiri Mascot',25), HubCategory('ramen','Ramen Mascot',25), HubCategory('tempura','Tempura Mascot',25),
    HubCategory('trailblazer-finish','Trailblazer Finish',11),
)

_CATEGORY_MAP={
    'landmark':'landmark','player house':'house','house':'house','car meet':'car_meet','drag meet':'drag_meetup',
    'day trip':'day_trip','drift club japan':'drift_club','moto auto zine':'moto_auto_zine',"yuji s auto":'yuji_auto',"yuji's auto":'yuji_auto',
    'food delivery job':'raku_raku_job','festival site':'festival_site','horizon event':'world_event',
    'danger sign':'danger_sign','drift zone':'drift_zone','speed trap':'speed_trap','speed zone':'speed_zone',
    'trailblazer':'trailblazer','trailblazer start gate':'trailblazer','trailblazer finish':'trailblazer','trailblazer finish gate':'trailblazer',
    'cross country event':'cross_country_race','cross country racing event':'cross_country_race','cross-country event':'cross_country_race',
    'road racing event':'road_race','street racing event':'street_race','dirt racing event':'rally_race','rally racing event':'rally_race',
    'touge racing event':'touge_race','time attack':'time_attack','time attack event':'time_attack','drag racing event':'drag_race',
    'barn find':'barn_find','treasure car':'treasure_car','bonus board':'xp_board','xp board':'xp_board','aftermarket car':'used_car',
    'photo location':'photo_spot','photo subject':'photo_spot','story chapter':'story','other':'other_discovery',
}


def category_from_title(title: str) -> str:
    key=normalize_text(title).replace('-',' ')
    if key.endswith(' mascot') or key in {'curry','dango','edamame','kakigori','matcha','omurice','onigiri','ramen','tempura'}:
        return 'mascot'
    return _CATEGORY_MAP.get(key,'collectible' if 'collect' in key else 'other_discovery')


def hub_latlng_to_world(lat: float, lng: float) -> tuple[float,float]:
    # Same WebMercator and telemetry calibration as static/nav_logic.js.
    tile_zoom=14; world_size=256*(2**tile_zoom)
    lat_rad=float(lat)*math.pi/180.0
    px=(float(lng)+180.0)/360.0*world_size
    py=(1.0-math.asinh(math.tan(lat_rad))/math.pi)/2.0*world_size
    a_world=(-119.49154,3888.595); a_pix=(2089486.0,2087415.0)
    b_world=(-7104.7695,-1863.08); b_pix=(2086885.0,2089556.0)
    mx=(b_pix[0]-a_pix[0])/(b_world[0]-a_world[0]); mz=(b_pix[1]-a_pix[1])/(b_world[1]-a_world[1])
    bx=a_pix[0]-mx*a_world[0]; by=a_pix[1]-mz*a_world[1]
    return (px-bx)/mx,(py-by)/mz


def _balanced_json_after(text: str, marker: str) -> dict | None:
    start=text.find(marker)
    if start<0:return None
    start=text.find('{',start+len(marker))
    if start<0:return None
    depth=0; in_string=False; escape=False
    for i,ch in enumerate(text[start:],start=start):
        if escape: escape=False; continue
        if ch=='\\' and in_string: escape=True; continue
        if ch=='"': in_string=not in_string; continue
        if in_string: continue
        if ch=='{': depth+=1
        elif ch=='}':
            depth-=1
            if depth==0:
                try:return json.loads(text[start:i+1])
                except json.JSONDecodeError:return None
    return None


def extract_mapgenie_map_data(html: str) -> dict | None:
    for marker in ('window.mapData =','window.mapData=','var mapData =','const mapData ='):
        doc=_balanced_json_after(html,marker)
        if isinstance(doc,dict) and isinstance(doc.get('locations'),list):return doc
    return None


def _category_lookup(data: dict) -> dict[int,str]:
    cats=data.get('categories') or {}
    values=cats.values() if isinstance(cats,dict) else cats
    out={}
    for c in values or []:
        if not isinstance(c,dict):continue
        try:cid=int(c.get('id'))
        except Exception:continue
        out[cid]=str(c.get('title') or c.get('name') or 'Other')
    return out


def records_from_mapgenie(data: dict, *, retrieved_at: str | None=None):
    cats=_category_lookup(data); records=[]; media={}
    for loc in data.get('locations') or []:
        if not isinstance(loc,dict):continue
        try:
            sid=str(loc.get('id'))
            name=str(loc.get('title') or loc.get('name') or '').strip()
            lat=float(loc.get('latitude')); lng=float(loc.get('longitude'))
            cid=int(loc.get('category_id'))
        except Exception:continue
        if not sid or sid=='None' or not name:continue
        cat_title=cats.get(cid,'Other'); category=category_from_title(cat_title)
        wx,wz=hub_latlng_to_world(lat,lng)
        src_url=f'{MAPGENIE_URL}?locationIds={urllib.parse.quote(sid)}'
        records.append(RawPlace(provider='mapgenie',source_id=sid,name=name,category=category,world_x=wx,world_z=wz,tags=(cat_title,),sources=(SourceRef('mapgenie',sid,src_url,retrieved_at),)))
        urls=extract_image_urls({'media':loc.get('media'), 'description':loc.get('description')})
        if urls:media[sid]=urls
    return records,media

_TAG_RE=re.compile(r'<[^>]+>')
_REGION_RE=re.compile(r'<h2[^>]*>\s*([^<(]+?)\s*(?:\([^<]*\))?\s*</h2>',re.I|re.S)
_ROW_RE=re.compile(
    r'<h3[^>]*>(?P<name>.*?)</h3>.*?href=["\'](?P<href>[^"\']*\bloc=(?P<id>\d+)[^"\']*)["\'].*?</a>.*?(?P<lat>-?\d+\.\d+)\s*,\s*(?P<lng>-?\d+\.\d+)',
    re.I|re.S,
)

def _plain(fragment: str) -> str:
    return re.sub(r'\s+',' ',html_lib.unescape(_TAG_RE.sub(' ',fragment))).strip()


def parse_hub_category_html(html: str, *, slug: str, provider_category: str, retrieved_at: str | None=None) -> list[RawPlace]:
    results=[]
    category=category_from_title(provider_category)
    regions=[(m.start(),_plain(m.group(1))) for m in _REGION_RE.finditer(html)]
    for m in _ROW_RE.finditer(html):
        name=_plain(m.group('name')); sid=m.group('id'); lat=float(m.group('lat')); lng=float(m.group('lng'))
        region=None
        for pos,label in regions:
            if pos<m.start():region=label
            else:break
        wx,wz=hub_latlng_to_world(lat,lng)
        href=html_lib.unescape(m.group('href'))
        url=urllib.parse.urljoin(HUB_BASE,href)
        results.append(RawPlace(provider='forzahorizonhub',source_id=sid,name=name,category=category,world_x=wx,world_z=wz,region=region,tags=(provider_category,),sources=(SourceRef('forzahorizonhub',sid,url,retrieved_at),)))
    return results


def _request(url: str, *, timeout: float=18.0) -> tuple[bytes,str|None]:
    req=urllib.request.Request(url,headers={'User-Agent':USER_AGENT,'Accept':'text/html,application/xhtml+xml,image/avif,image/webp,image/*,*/*;q=0.8'})
    with urllib.request.urlopen(req,timeout=timeout) as response:
        return response.read(),response.headers.get_content_type()


def fetch_full_records(fetch: Callable[[str],tuple[bytes,str|None]]|None=None, *, min_records:int=700):
    fetch=fetch or _request; retrieved=datetime.now(timezone.utc).date().isoformat()
    errors=[]
    # Preferred: MapGenie exposes all locations and media in one window.mapData payload.
    try:
        raw,_=fetch(MAPGENIE_URL); data=extract_mapgenie_map_data(raw.decode('utf-8','replace'))
        if data:
            records,media=records_from_mapgenie(data,retrieved_at=retrieved)
            if len(records)>=min_records:return records,media,{'provider':'mapgenie','errors':errors}
            errors.append(f'MapGenie returned only {len(records)} positioned records')
    except Exception as exc:errors.append(f'MapGenie: {exc}')
    # Fallback: server-rendered FH Hub category pages. They expose all 796 marker coordinates.
    rows=[]
    def one(cat:HubCategory):
        url=f'{HUB_BASE}/{cat.slug}'
        raw,_=fetch(url)
        return cat,parse_hub_category_html(raw.decode('utf-8','replace'),slug=cat.slug,provider_category=cat.title,retrieved_at=retrieved)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        future_map={ex.submit(one,c):c for c in HUB_CATEGORIES}
        for fut,c in list(future_map.items()):
            try:
                cat,got=fut.result(); rows.extend(got)
                if len(got)!=cat.count:errors.append(f'{cat.slug}: expected {cat.count}, parsed {len(got)}')
            except Exception as exc:errors.append(f'{c.slug}: {exc}')
    return rows,{}, {'provider':'forzahorizonhub','errors':errors}


def _atomic_json(path:Path,doc:dict):
    path.parent.mkdir(parents=True,exist_ok=True)
    data=(json.dumps(doc,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf-8')
    fd,tmp=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        try:os.unlink(tmp)
        except FileNotFoundError:pass


def _state_age_hours(state:dict) -> float:
    try:return max(0,(time.time()-float(state.get('timestamp',0)))/3600)
    except Exception:return 1e9


def bootstrap_catalog(*, root:Path, force:bool=False, fetch=None, min_records:int=700, media_limit:int=180) -> dict:
    root=Path(root); state_path=root/'data'/'catalog_bootstrap_state.json'; output=root/'static'/'data'/'builtin_places.json'
    media_root=root/'static'/'media'/'places'; graph_path=root/'static'/'data'/'fh6_navgraph_v1.json.gz'
    try:state=json.loads(state_path.read_text(encoding='utf-8'))
    except Exception:state={}
    if not force and state.get('success') and _state_age_hours(state)<24*7 and output.is_file():
        return {'status':'fresh','runtime_places':state.get('runtime_places',0),'media_cached':state.get('media_cached',0),'provider':state.get('provider')}
    if not force and not state.get('success') and _state_age_hours(state)<6:
        return {'status':'cooldown','error':state.get('error','previous bootstrap failed')}
    try:
        records,media,meta=fetch_full_records(fetch=fetch,min_records=min_records)
        if len(records)<min_records:raise RuntimeError(f'only {len(records)} positioned records were acquired; keeping bundled catalog')
        graph=load_navgraph(graph_path); snapper=NavGraphSnapper(graph)
        doc=build_runtime_catalog(records,catalog_version='2026.08.30.v1.17',snapper=snapper)
        doc['build'].update({'reported_source_markers':796,'coordinate_records_captured':len(records),'source_provider':meta['provider'],'source_errors':meta['errors'][:20]})
        # Cache screenshots before publishing the new catalog. Failures never remove the place.
        cached=0
        if media:
            record_by_source={r.source_id:r for r in records}
            priorities={'landmark':0,'photo_spot':0,'house':1,'festival_site':1,'world_event':1,'story':1,'barn_find':1,'treasure_car':1,'used_car':1,'car_meet':1}
            tasks=[]
            for sid,urls in media.items():
                rec=record_by_source.get(sid)
                if rec and urls and rec.category in priorities:tasks.append((priorities[rec.category],sid,rec,urls[0]))
            tasks.sort(key=lambda x:(x[0],x[1])); tasks=tasks[:media_limit]
            def cache_one(item):
                _,sid,rec,url=item; raw,ctype=(fetch or _request)(url)
                pid=stable_place_id('game',rec.category,rec.name)
                local=cache_image_bytes(raw,content_type=ctype,stable_id=pid,media_root=media_root)
                return pid,url,local
            with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
                for fut in [ex.submit(cache_one,t) for t in tasks]:
                    try:
                        pid,url,local=fut.result();
                        for p in doc['places']:
                            if p['id']==pid:
                                p.update(local);p['image_source']=meta['provider'];p['image_attribution']='Source screenshot cached locally';break
                        cached+=1
                    except Exception:pass
        _atomic_json(output,doc)
        state={'success':True,'timestamp':time.time(),'provider':meta['provider'],'input_records':len(records),'runtime_places':len(doc['places']),'snapped_places':doc['build']['snapped_places'],'media_cached':cached,'errors':meta['errors'][:20]}
        _atomic_json(state_path,state)
        return {'status':'updated',**state}
    except Exception as exc:
        state={'success':False,'timestamp':time.time(),'error':str(exc)};_atomic_json(state_path,state)
        return {'status':'offline_fallback','error':str(exc)}


def main(argv=None):
    import argparse
    p=argparse.ArgumentParser(description='DEVELOPER-ONLY network source refresh. Normal Navigator startup never calls this tool.')
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2]);p.add_argument('--force',action='store_true')
    args=p.parse_args(argv);result=bootstrap_catalog(root=args.root,force=args.force);print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result.get('status') in {'updated','fresh'} else 1

if __name__=='__main__':raise SystemExit(main())
