"""Read-only FH6 StringTables adapter used to cache official POI display names.

The .str layout follows the public MIT-licensed ForzaTech localization toolkit.
This module never modifies game files. It only reads EN/CHS/RU/MX archives and
writes Navigator's own static/data/place_names.json cache.
"""
from __future__ import annotations
import json, os, re, struct, zipfile
from pathlib import Path

ARCHIVES={'en-US':'EN.zip','zh-CN':'CHS.zip','ru-RU':'RU.zip','es-419':'MX.zip'}


def _cstring(blob:bytes, offset:int)->str:
    if offset<0 or offset>=len(blob): return ''
    end=blob.find(b'\0',offset)
    if end<0:end=len(blob)
    return blob[offset:end].decode('utf-8',errors='replace')


def _parse_section(data:bytes, offset:int):
    if offset+12>len(data):raise ValueError('truncated string-table section')
    size,blob_size,count=struct.unpack_from('<III',data,offset)
    entries_off=offset+12; blob_off=entries_off+8*count
    if size<12+8*count or blob_off+blob_size>len(data):raise ValueError('invalid string-table section bounds')
    out=[]
    for i in range(count):
        h,rel=struct.unpack_from('<II',data,entries_off+i*8)
        out.append((h,_cstring(data,blob_off+rel)))
    return out


def parse_str_bytes(data:bytes)->dict:
    if len(data)<0x8c or data[:2]!=b'\x00\x08':raise ValueError('not a supported ForzaTech .str')
    table=_cstring(data,2)
    values_off,keys_off=struct.unpack_from('<II',data,0x84)
    values=_parse_section(data,values_off);keys=_parse_section(data,keys_off)
    if len(values)!=len(keys):raise ValueError('mismatched string-table sections')
    entries=[]
    for (vh,value),(kh,key) in zip(values,keys):
        if vh!=kh:raise ValueError('key/value hash mismatch')
        entries.append({'hash':vh,'key':key,'value':value})
    return {'table':table,'entries':entries}


def read_stringtable_zip(path:Path)->dict:
    tables={}
    with zipfile.ZipFile(path,'r') as z:
        for name in z.namelist():
            if not name.lower().endswith('.str'):continue
            try:doc=parse_str_bytes(z.read(name))
            except (ValueError,KeyError,NotImplementedError):continue
            tables[doc['table']]={e['hash']:e for e in doc['entries']}
    return tables


def _norm(value):return ' '.join(str(value or '').strip().casefold().split())


def build_place_name_map(places:list[dict], stringtables_dir:Path)->dict:
    root=Path(stringtables_dir)
    if not (root/'EN.zip').is_file():return {}
    locale_tables={}
    for locale,filename in ARCHIVES.items():
        path=root/filename
        if path.is_file():
            try:locale_tables[locale]=read_stringtable_zip(path)
            except (OSError,zipfile.BadZipFile):pass
    en=locale_tables.get('en-US',{})
    value_index={}
    for table,rows in en.items():
        for h,e in rows.items():value_index.setdefault(_norm(e['value']),[]).append((table,h,e['value']))
    out={}
    for p in places:
        if p.get('source') not in {'game','curated'}:continue
        canonical=str(p.get('game') or p.get('name') or '').strip()
        matches=value_index.get(_norm(canonical),[])
        if len(matches)!=1:continue
        table,h,english=matches[0];row={'en-US':english}
        for locale,tables in locale_tables.items():
            if locale=='en-US':continue
            value=tables.get(table,{}).get(h,{}).get('value')
            if value:row[locale]=value
        out[str(p['id'])]=row
    return out


def _stringtables_candidates_from_game_root(root:Path):
    root=Path(root)
    return [
        root,
        root/'media'/'Stripped'/'StringTables',
        root/'Content'/'media'/'Stripped'/'StringTables',
    ]


def _steam_library_paths(steam_root:Path)->list[Path]:
    roots=[Path(steam_root)]
    config=Path(steam_root)/'steamapps'/'libraryfolders.vdf'
    try:text=config.read_text(encoding='utf-8',errors='replace')
    except OSError:return roots
    for raw in re.findall(r'"path"\s*"([^"]+)"',text,re.I):
        value=raw.replace('\\\\','\\')
        path=Path(value)
        if path not in roots:roots.append(path)
    return roots


def _default_steam_roots()->list[Path]:
    values=[]
    for env in ('STEAM_PATH','PROGRAMFILES(X86)','PROGRAMFILES','ProgramW6432'):
        raw=os.environ.get(env)
        if not raw:continue
        p=Path(raw)
        if env!='STEAM_PATH':p=p/'Steam'
        if p not in values:values.append(p)
    for p in (Path('C:/Program Files (x86)/Steam'),Path('C:/Program Files/Steam')):
        if p not in values:values.append(p)
    return values


def _default_xbox_roots()->list[Path]:
    values=[]
    explicit=os.environ.get('XBOX_GAMES_ROOT')
    if explicit:values.append(Path(explicit))
    drive=os.environ.get('SystemDrive','C:')
    for prefix in [drive,*[f'{c}:' for c in 'CDEFGHIJKLMNOPQRSTUVWXYZ']]:
        p=Path(f'{prefix}/XboxGames')
        if p not in values:values.append(p)
    return values


def find_stringtables_dir(explicit:Path|None=None, *, steam_roots:list[Path]|None=None, xbox_roots:list[Path]|None=None)->Path|None:
    candidates=[]
    if explicit:candidates += _stringtables_candidates_from_game_root(Path(explicit))
    for env in ('FH6_STRINGTABLES_DIR','FH6_PATH','FORZA_HORIZON_6_PATH'):
        if os.environ.get(env):candidates += _stringtables_candidates_from_game_root(Path(os.environ[env]))

    steam_roots=_default_steam_roots() if steam_roots is None else [Path(p) for p in steam_roots]
    for steam_root in steam_roots:
        for library in _steam_library_paths(steam_root):
            common=library/'steamapps'/'common'
            for name in ('ForzaHorizon6','Forza Horizon 6'):
                candidates += _stringtables_candidates_from_game_root(common/name)

    xbox_roots=_default_xbox_roots() if xbox_roots is None else [Path(p) for p in xbox_roots]
    for xbox_root in xbox_roots:
        for name in ('Forza Horizon 6','ForzaHorizon6'):
            candidates += _stringtables_candidates_from_game_root(xbox_root/name)

    seen=set()
    for p in candidates:
        key=str(p).casefold()
        if key in seen:continue
        seen.add(key)
        if p.is_dir() and (p/'EN.zip').is_file():return p
    return None


def localization_coverage(names:dict,total_game_places:int)->dict:
    total=max(0,int(total_game_places or 0))
    game_rows={key:row for key,row in (names or {}).items() if not str(key).startswith(('curated.','community.','user.'))}
    result={}
    for locale in ARCHIVES:
        matched=sum(1 for row in game_rows.values() if isinstance(row,dict) and str(row.get(locale) or '').strip())
        result[locale]={'matched':min(matched,total) if total else matched,'total':total}
    return result


def _load_places(path:Path):
    try:data=json.loads(path.read_text(encoding='utf-8'))
    except (OSError,json.JSONDecodeError):return []
    if isinstance(data,list):return data
    if isinstance(data,dict):return data.get('places') or []
    return []


def refresh_place_names(static_dir:Path, stringtables_dir:Path|None=None, target:Path|None=None)->dict:
    static=Path(static_dir);root=find_stringtables_dir(stringtables_dir)
    target=Path(target or static/'data'/'place_names.json')
    if root is None:
        try:return json.loads(target.read_text(encoding='utf-8')) if target.is_file() else {}
        except Exception:return {}
    places=_load_places(static/'data'/'builtin_places.json')+_load_places(static/'data'/'scenic_catalog.json')
    names=build_place_name_map(places,root)
    target.parent.mkdir(parents=True,exist_ok=True);tmp=target.with_suffix('.tmp')
    tmp.write_text(json.dumps(names,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(tmp,target)
    return names
