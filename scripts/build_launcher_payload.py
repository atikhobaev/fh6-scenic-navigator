#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EXCLUDED_TOP={'.git','.worktrees','tests','docs','launcher_native','cmd','launcher_payload','node_modules'}
EXCLUDED_NAMES={'start.bat','update_map_data.bat','run_tests.bat','probe_game_nav_assets.bat','probe_nav_binary_samples.bat','package.json','package-lock.json','go.mod','go.sum'}
ALLOWED_TOP_EXT={'.py','.txt','.md','.ps1'}

def should_include(p:Path)->bool:
    rel=p.relative_to(ROOT)
    if not rel.parts: return False
    if rel.parts[0] in EXCLUDED_TOP: return False
    if p.name in EXCLUDED_NAMES: return False
    if '__pycache__' in rel.parts or p.suffix in {'.pyc','.pyo'}: return False
    if rel.parts[0]=='static' or rel.parts[0]=='fh6_nav': return p.is_file()
    return len(rel.parts)==1 and p.suffix.lower() in ALLOWED_TOP_EXT and p.is_file()

def build(out:Path,version:str)->dict:
    files=sorted((p for p in ROOT.rglob('*') if should_include(p)),key=lambda p:p.relative_to(ROOT).as_posix())
    out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in files:
            info=zipfile.ZipInfo(p.relative_to(ROOT).as_posix(),date_time=(2026,8,30,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o644<<16
            z.writestr(info,p.read_bytes())
        manifest=json.dumps({'version':version,'files':len(files)},sort_keys=True,separators=(',',':')).encode()
        info=zipfile.ZipInfo('portable_manifest.json',date_time=(2026,8,30,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,manifest)
    data=out.read_bytes()
    return {'version':version,'files':len(files),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',default='launcher_native/assets/app_payload.zip');ap.add_argument('--version',default='1.19.2');a=ap.parse_args()
    report=build(ROOT/a.out,a.version)
    print(json.dumps(report,indent=2))
