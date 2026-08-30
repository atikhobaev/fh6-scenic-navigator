from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib
from .binary import Reader, align_up
from .errors import CorruptWvanError, UnsupportedWvanError

@dataclass(frozen=True)
class NavPoint:
    id: int
    x: float
    y: float
    z: float
    nx: float
    ny: float
    nz: float
    metadata_start: int | None

@dataclass(frozen=True)
class RawSection:
    id: int
    sequence_start: int
    sequence_count: int
    metadata_start: int
    opaque: tuple[int, int, int, int]

@dataclass(frozen=True)
class MetadataRecord:
    id: int
    key_id: int
    value_id: int

@dataclass(frozen=True)
class EntityMetadata:
    start: int
    end: int
    values: tuple[tuple[str, str], ...]

@dataclass(frozen=True)
class WvanDocument:
    source_path: str
    source_sha256: str
    source_size: int
    points: tuple[NavPoint, ...]
    sections: tuple[RawSection, ...]
    point_sequence: tuple[int, ...]
    metadata_records: tuple[MetadataRecord, ...]
    metadata_keys: tuple[str, ...]
    metadata_values: tuple[str, ...]
    section_metadata: dict[int, EntityMetadata]
    point_metadata: dict[int, EntityMetadata]
    value_offset_mode: str
    footer_offset: int


def _decode_strings(r, start, blob_size, offsets, label):
    r.read(start, blob_size)
    result=[]
    for off in offsets:
        if off >= blob_size:
            raise CorruptWvanError(f'{r.source}: {label} offset {off} >= blob {blob_size}')
        raw=r.read(start+off, blob_size-off)
        nul=raw.find(b'\0')
        if nul < 0: raise CorruptWvanError(f'{r.source}: unterminated {label} string')
        s=raw[:nul]
        if any(b < 32 or b >= 127 for b in s):
            raise CorruptWvanError(f'{r.source}: non-ASCII {label} string')
        result.append(s.decode('ascii'))
    return tuple(result)


def _candidate_strings(r, meta_end, key_count, value_count, key_blob_size, value_blob_size, metadata, shifted):
    key_offsets=[r.u64(meta_end+i*8) for i in range(key_count)]
    value_off_base=meta_end+key_count*8
    stored_count=value_count+(1 if shifted else 0)
    stored=[r.u64(value_off_base+i*8) for i in range(stored_count)]
    offsets_end=value_off_base+stored_count*8
    key_blob=align_up(offsets_end,16)
    if any(r.read(offsets_end,key_blob-offsets_end)):
        raise CorruptWvanError(f'{r.source}: non-zero offset-table alignment padding')
    keys=_decode_strings(r,key_blob,key_blob_size,key_offsets,'key') if key_count else ()
    value_blob=align_up(key_blob+key_blob_size,16)
    voffs=stored[1:] if shifted else stored
    values=_decode_strings(r,value_blob,value_blob_size,voffs,'value') if value_count else ()
    for rec in metadata:
        if rec.key_id >= len(keys) or rec.value_id >= len(values):
            raise CorruptWvanError(f'{r.source}: metadata key/value id out of range')
    footer=align_up(value_blob+value_blob_size,16)
    if r.read(footer,4) != b'WVAN' or r.u32(footer+4) != 0x200:
        raise CorruptWvanError(f'{r.source}: WVAN footer not found for candidate')
    return keys,values,footer


def _group_metadata(points, sections, records, keys, values, metadata_count):
    entities=[]
    for s in sections:
        entities.append((s.metadata_start,'section',s.id))
    for p in points:
        if p.metadata_start is not None:
            entities.append((p.metadata_start,'point',p.id))
    if any(start < 0 or start >= metadata_count for start,_,_ in entities):
        raise CorruptWvanError('metadata entity start outside metadata table')
    starts=[x[0] for x in entities]
    if len(starts) != len(set(starts)):
        raise CorruptWvanError('duplicate metadata entity start')
    entities.sort()
    section_meta={}; point_meta={}
    for i,(start,kind,eid) in enumerate(entities):
        end=entities[i+1][0] if i+1 < len(entities) else metadata_count
        vals=tuple((keys[r.key_id],values[r.value_id]) for r in records[start:end])
        ent=EntityMetadata(start,end,vals)
        (section_meta if kind=='section' else point_meta)[eid]=ent
    return section_meta,point_meta


def parse_wvan_bytes(data: bytes, source='<bytes>') -> WvanDocument:
    r=Reader(data,source)
    if r.size < 0x80 or r.read(0,4) != b'WVAN' or r.u32(4) != 0x200:
        raise UnsupportedWvanError(f'{source}: unsupported WVAN layout')
    nav_count,section_count,seq_count,aux_count,meta_count,key_count,value_count,key_blob_size,value_blob_size,_opaque = r.unpack('<10I',0x58)
    nav_off=0x80; nav_end=nav_off+nav_count*0x30
    sec_off=nav_end; sec_end=sec_off+section_count*0x18
    seq_off=align_up(sec_end,16); seq_end=seq_off+seq_count*8
    aux_off=align_up(seq_end,16); aux_end=aux_off+aux_count*16
    meta_off=aux_end; meta_end=meta_off+meta_count*16
    if meta_end > r.size: raise CorruptWvanError(f'{source}: WVAN tables exceed file')

    points=[]
    for i in range(nav_count):
        off=nav_off+i*0x30
        prefix=r.unpack('<4I',off)
        x,y,z=r.unpack('<3f',off+16); nx,ny,nz=r.unpack('<3f',off+28)
        m=None if prefix[2] == 0xffffffff else int(prefix[2])
        points.append(NavPoint(i,x,y,z,nx,ny,nz,m))
    sections=[]
    for i in range(section_count):
        v=r.unpack('<6I',sec_off+i*0x18)
        sections.append(RawSection(i,int(v[0]),int(v[4]),int(v[2]),(int(v[1]),int(v[3]),int(v[5]),0)))
    seq=tuple(int(r.u64(seq_off+i*8)) for i in range(seq_count))
    if any(pid >= nav_count for pid in seq): raise CorruptWvanError(f'{source}: sequence point out of range')
    for i,s in enumerate(sections):
        if s.sequence_start+s.sequence_count > seq_count: raise CorruptWvanError(f'{source}: section range out of bounds')
        if i+1 < len(sections) and s.sequence_start+s.sequence_count != sections[i+1].sequence_start:
            raise CorruptWvanError(f'{source}: section sequence partition gap at {i}')
    if sections and sections[-1].sequence_start+sections[-1].sequence_count != seq_count:
        raise CorruptWvanError(f'{source}: section partition does not consume sequence')
    metadata=tuple(MetadataRecord(i,*r.unpack('<QQ',meta_off+i*16)) for i in range(meta_count))
    candidates=[]
    for shifted in (False,True):
        try:
            candidates.append(('shifted' if shifted else 'direct', *_candidate_strings(r,meta_end,key_count,value_count,key_blob_size,value_blob_size,metadata,shifted)))
        except CorruptWvanError:
            pass
    if not candidates: raise CorruptWvanError(f'{source}: metadata string layout unresolved')
    # Exact header value_count wins when both align structurally; shifted is fallback for known Brio layout.
    candidate=next((c for c in candidates if c[0]=='direct'),candidates[0])
    mode,keys,values,footer=candidate
    sm,pm=_group_metadata(points,sections,metadata,keys,values,meta_count)
    raw=bytes(data)
    return WvanDocument(str(source),hashlib.sha256(raw).hexdigest(),len(raw),tuple(points),tuple(sections),seq,metadata,keys,values,sm,pm,mode,footer)


def parse_wvan_file(path):
    p=Path(path)
    return parse_wvan_bytes(p.read_bytes(),str(p))
