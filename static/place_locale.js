import {getLocale,normalizedLocale} from './i18n.js';
let NAMES={};
export async function loadPlaceNames(url='/data/place_names.json'){
  try{const r=await fetch(url,{cache:'no-store'});if(r.ok){const j=await r.json();NAMES=j&&typeof j==='object'?j:{}}}catch{}
  return NAMES;
}
export function setPlaceNamesMap(value){NAMES=value&&typeof value==='object'?value:{};return NAMES}
export function getPlaceNamesMap(){return NAMES}

function stableIdLike(value=''){
  return /^(?:builtin|community|curated|user)\./i.test(String(value||'').trim());
}

export function humanizeStablePlaceId(value=''){
  const raw=String(value||'').trim();
  if(!raw)return '';
  const leaf=raw.split('.').filter(Boolean).at(-1)||raw;
  const match=leaf.match(/^(.*?)[_-](\d{2,})$/);
  const base=(match?match[1]:leaf).replace(/[_-]+/g,' ').replace(/\b\w/g,c=>c.toUpperCase()).trim();
  return match?`${base} #${match[2]}`:base;
}

export function localizedPlaceName(place={},locale=getLocale(),names=NAMES){
  const id=String(place?.id||''),loc=normalizedLocale(locale),row=names?.[id]||place?.names||{};
  const selected=String(row?.[loc]||'').trim();if(selected)return selected;
  const english=String(row?.['en-US']||place?.game||place?.name||'').trim();
  if(english&&!stableIdLike(english))return english;
  const fallback=String(place?.name||'').trim();
  if(fallback&&!stableIdLike(fallback))return fallback;
  return humanizeStablePlaceId(id||fallback);
}

export function localizedGameName(englishName,locale=getLocale(),names=NAMES){
  const english=String(englishName||'').trim();
  if(!english)return '';
  const needle=english.toLocaleLowerCase('en-US');
  const matches=Object.values(names||{}).filter(row=>String(row?.['en-US']||'').trim().toLocaleLowerCase('en-US')===needle);
  if(matches.length!==1)return stableIdLike(english)?humanizeStablePlaceId(english):english;
  const row=matches[0],loc=normalizedLocale(locale);
  return row?.[loc]||row?.['en-US']||english;
}

export function localizedRouteItemName(item={},placesById=new Map(),locale=getLocale(),names=NAMES){
  const custom=String(item?.custom_label||'').trim();
  if(custom)return custom;
  const id=String(item?.place_id||'').trim();
  if(id){
    const place=typeof placesById?.get==='function'?placesById.get(id):placesById?.[id];
    if(place){
      const label=localizedPlaceName(place,locale,names);
      if(label)return label;
    }
    const supplied=String(item?.place_name||'').trim();
    if(supplied&&supplied!==id&&!stableIdLike(supplied))return localizedGameName(supplied,locale,names);
    return humanizeStablePlaceId(id);
  }
  const supplied=String(item?.place_name||'').trim();
  if(supplied)return localizedGameName(supplied,locale,names);
  const scenic=String(item?.scenic_block_id||'').trim();
  return scenic?humanizeStablePlaceId(scenic):'';
}

export function localizedSourceLabel(source=''){return String(source||'').replace(/^./,s=>s.toUpperCase())}
