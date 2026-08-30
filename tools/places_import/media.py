from __future__ import annotations

import hashlib
import html as html_lib
import io
import re
from pathlib import Path
from urllib.parse import urlparse

_IMAGE_RE = re.compile(r'https?://[^\s"\'<>]+?\.(?:jpe?g|png|webp)(?:\?[^\s"\'<>]*)?', re.I)
_IMG_TAG_RE = re.compile(r'<img[^>]+(?:src|data-src)=["\']([^"\']+)["\']', re.I)


def _walk_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _walk_strings(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from _walk_strings(v)


def extract_image_urls(value) -> list[str]:
    out=[]
    seen=set()
    for text in _walk_strings(value):
        candidates=[]
        if text.startswith(('http://','https://')):
            candidates.append(text)
        candidates.extend(_IMG_TAG_RE.findall(text))
        candidates.extend(_IMAGE_RE.findall(text))
        for raw in candidates:
            url=html_lib.unescape(raw).strip()
            if not url.startswith(('http://','https://')):
                continue
            low=url.lower()
            if any(bad in low for bad in ('marker','sprite','favicon','icon@','markers@')):
                continue
            if url not in seen:
                seen.add(url); out.append(url)
    return out


def _safe_stem(stable_id: str) -> str:
    stem=re.sub(r'[^a-z0-9._-]+','-',stable_id.lower()).strip('-._')
    return stem[:150] or hashlib.sha256(stable_id.encode()).hexdigest()[:20]


def _ext_from(content_type: str | None, data: bytes) -> str:
    c=(content_type or '').lower()
    if 'webp' in c or data.startswith(b'RIFF') and data[8:12]==b'WEBP': return '.webp'
    if 'png' in c or data.startswith(b'\x89PNG'): return '.png'
    if 'jpeg' in c or 'jpg' in c or data.startswith(b'\xff\xd8'): return '.jpg'
    return '.img'


def cache_image_bytes(data: bytes, *, content_type: str | None, stable_id: str, media_root: Path, allow_pillow: bool=True) -> dict:
    if not data: raise ValueError('empty image payload')
    media_root=Path(media_root); media_root.mkdir(parents=True,exist_ok=True)
    stem=_safe_stem(stable_id)
    sha=hashlib.sha256(data).hexdigest()
    if allow_pillow:
        try:
            from PIL import Image, ImageOps
            with Image.open(io.BytesIO(data)) as im0:
                im=ImageOps.exif_transpose(im0).convert('RGB')
                full=im.copy(); full.thumbnail((1600,1600))
                thumb=im.copy(); thumb.thumbnail((480,480))
                full_path=media_root/f'{stem}.webp'; thumb_path=media_root/f'{stem}.thumb.webp'
                full.save(full_path,'WEBP',quality=86,method=6)
                thumb.save(thumb_path,'WEBP',quality=80,method=6)
            return {
                'image':f'/media/places/{full_path.name}',
                'image_thumb':f'/media/places/{thumb_path.name}',
                'image_sha256':sha,
            }
        except Exception:
            pass
    ext=_ext_from(content_type,data)
    path=media_root/f'{stem}{ext}'
    path.write_bytes(data)
    local=f'/media/places/{path.name}'
    return {'image':local,'image_thumb':local,'image_sha256':sha}
