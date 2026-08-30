function norm(s=''){
  return String(s).normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9а-яё]+/giu,' ').trim().replace(/\s+/g,' ');
}

function lev(a,b,limit=3){
  if(a===b)return 0;
  if(Math.abs(a.length-b.length)>limit)return limit+1;
  let prev=Array.from({length:b.length+1},(_,i)=>i);
  for(let i=1;i<=a.length;i++){
    const cur=[i]; let rowMin=i;
    for(let j=1;j<=b.length;j++){
      const v=Math.min(cur[j-1]+1,prev[j]+1,prev[j-1]+(a[i-1]===b[j-1]?0:1));
      cur[j]=v; rowMin=Math.min(rowMin,v);
    }
    if(rowMin>limit)return limit+1;
    prev=cur;
  }
  return prev[b.length];
}

function tokensFor(p){
  const fields=[p.name,...(p.aliases||[]),p.category,p.subcategory,...(p.tags||[]),p.region,p.collection];
  return norm(fields.filter(Boolean).join(' ')).split(' ').filter(Boolean);
}

export function buildSearchIndex(places){
  return (places||[]).map((place,ordinal)=>({place,ordinal,tokens:tokensFor(place),text:norm([place.name,...(place.aliases||[]),...(place.tags||[])].join(' '))}));
}

function matchScore(entry,q){
  if(!q)return 0;
  const qt=norm(q).split(' ').filter(Boolean); if(!qt.length)return 0;
  let total=0;
  for(const token of qt){
    let best=Infinity;
    for(const t of entry.tokens){
      if(t===token){best=0;break;}
      if(t.startsWith(token)||token.startsWith(t))best=Math.min(best,0.35);
      else if(t.includes(token)||token.includes(t))best=Math.min(best,0.6);
      else {
        const max=Math.max(1,Math.min(3,Math.floor(Math.max(t.length,token.length)*0.34)));
        const d=lev(t,token,max); if(d<=max)best=Math.min(best,1+d/max);
      }
    }
    if(!Number.isFinite(best))return Infinity;
    total+=best;
  }
  return total;
}

function arrHas(filter,value){ return !Array.isArray(filter)||!filter.length||filter.includes(value); }

function passes(p,f={}){
  const mode=f.mode||'recommended';
  if(mode!=='all'&&!p.default_visible&&p.source!=='user')return false;
  if(f.favorites&&!p.favorite)return false;
  if(f.featured&&!p.featured)return false;
  if(f.myPlaces&&p.source!=='user')return false;
  if(!arrHas(f.categories,p.category))return false;
  if(!arrHas(f.surfaces,p.surface))return false;
  if(!arrHas(f.access,p.access))return false;
  if(!arrHas(f.sources,p.source))return false;
  if(!arrHas(f.quality,p.quality))return false;
  return true;
}

function recommendedScore(p){
  return (p.favorite?50:0)+(p.featured?30:0)+(Number(p.scenic_score)||0)*5+(p.quality==='verified'?8:p.quality==='reviewed'?5:0)+(p.source==='curated'?3:0);
}

export function searchPlaces(index,query='',filters={}){
  const scored=[];
  for(const entry of index||[]){
    const p=entry.place;if(!passes(p,filters))continue;
    const score=matchScore(entry,query);if(!Number.isFinite(score))continue;
    scored.push({p,score,ordinal:entry.ordinal});
  }
  const sort=filters.sort||'recommended';
  scored.sort((a,b)=>{
    if(query&&a.score!==b.score)return a.score-b.score;
    if(sort==='name')return String(a.p.name).localeCompare(String(b.p.name),undefined,{sensitivity:'base'})||a.ordinal-b.ordinal;
    if(sort==='scenic')return (Number(b.p.scenic_score)||0)-(Number(a.p.scenic_score)||0)||String(a.p.name).localeCompare(String(b.p.name));
    if(sort==='recent')return String(b.p.last_used_at||'').localeCompare(String(a.p.last_used_at||''))||a.ordinal-b.ordinal;
    return recommendedScore(b.p)-recommendedScore(a.p)||String(a.p.name).localeCompare(String(b.p.name));
  });
  const results=scored.map(x=>x.p);
  const categories={}; const surfaces={}; const sources={};
  for(const p of results){ categories[p.category]=(categories[p.category]||0)+1; surfaces[p.surface]=(surfaces[p.surface]||0)+1; sources[p.source]=(sources[p.source]||0)+1; }
  return {results,total:results.length,counts:{categories,surfaces,sources}};
}

export function activeFilterChips(filters={}){
  const out=[];
  if(filters.favorites)out.push({key:'favorites',label:'Favorites'});
  if(filters.featured)out.push({key:'featured',label:'Featured'});
  if(filters.myPlaces)out.push({key:'myPlaces',label:'My Places'});
  for(const v of filters.categories||[])out.push({key:`category:${v}`,label:v});
  for(const v of filters.surfaces||[])out.push({key:`surface:${v}`,label:v});
  for(const v of filters.access||[])out.push({key:`access:${v}`,label:v});
  for(const v of filters.sources||[])out.push({key:`source:${v}`,label:v});
  for(const v of filters.quality||[])out.push({key:`quality:${v}`,label:v});
  return out;
}

export { norm as normalizeSearchText };
