const DEG = 180 / Math.PI;

function clamp(v,a,b){ return Math.max(a,Math.min(b,v)); }
function normDeg(v){ return ((v%360)+360)%360; }
function angleError(a,b){ const d=Math.abs(normDeg(a)-normDeg(b)); return Math.min(d,360-d); }
function bearingWorld(a,b){ return normDeg(Math.atan2(b.x-a.x,b.z-a.z)*DEG); }
function bearingPixel(a,b){ return Math.atan2(b[0]-a[0],-(b[1]-a[1]))*DEG; }
function signedDelta(a,b){ return ((b-a+540)%360)-180; }
function key(cx,cz){ return `${cx},${cz}`; }

function project(world,a,b){
  const dx=b.x-a.x,dz=b.z-a.z, len2=dx*dx+dz*dz;
  const t=len2<=1e-9?0:clamp(((world.x-a.x)*dx+(world.z-a.z)*dz)/len2,0,1);
  const x=a.x+dx*t,z=a.z+dz*t;
  return {t,x,z,distance:Math.hypot(world.x-x,world.z-z)};
}

export function buildDirectedRuntime(payload,{bucketSize=220}={}){
  if(payload?.format!=='fh6-navgraph-v1' || !payload?.capabilities?.directed_segments || !payload?.capabilities?.turn_transitions){
    throw new Error('Authoritative directed WVAN graph is unavailable');
  }
  const points=(payload.points||[]).map(r=>({id:r[0],x:r[1],y:r[2],z:r[3]}));
  const segments=(payload.segments||[]).map(r=>({id:r[0],sectionId:r[1],from:r[2],to:r[3],length:r[4],oneway:Boolean(r[5]),roadType:r[6]||''}));
  const next=Array.from({length:segments.length},()=>[]);
  for(const [a,b] of payload.transitions||[]){ if(next[a] && segments[b]) next[a].push(b); }
  const segmentBuckets=new Map(), pointBuckets=new Map();
  const add=(map,k,v)=>{let a=map.get(k);if(!a){a=[];map.set(k,a);}a.push(v);};
  for(const p of points) add(pointBuckets,key(Math.floor(p.x/bucketSize),Math.floor(p.z/bucketSize)),p.id);
  for(const s of segments){
    const a=points[s.from],b=points[s.to]; if(!a||!b) continue;
    s.bearing=bearingWorld(a,b);
    const x0=Math.floor(Math.min(a.x,b.x)/bucketSize),x1=Math.floor(Math.max(a.x,b.x)/bucketSize);
    const z0=Math.floor(Math.min(a.z,b.z)/bucketSize),z1=Math.floor(Math.max(a.z,b.z)/bucketSize);
    for(let x=x0;x<=x1;x++) for(let z=z0;z<=z1;z++) add(segmentBuckets,key(x,z),s.id);
  }
  return {payload,points,segments,next,bucketSize,segmentBuckets,pointBuckets,capabilities:payload.capabilities,stats:payload.stats||{}};
}

function nearbyBucketValues(map,world,bucketSize,radiusCells){
  const cx=Math.floor(world.x/bucketSize),cz=Math.floor(world.z/bucketSize),out=[],seen=new Set();
  for(let dx=-radiusCells;dx<=radiusCells;dx++) for(let dz=-radiusCells;dz<=radiusCells;dz++){
    for(const id of map.get(key(cx+dx,cz+dz))||[]){ if(!seen.has(id)){seen.add(id);out.push(id);} }
  }
  return out;
}

export function nearestPointIds(world,rt,count=8){
  let ids=[];
  for(let r=0;r<=4 && ids.length<count;r++) ids=nearbyBucketValues(rt.pointBuckets,world,rt.bucketSize,r);
  if(!ids.length) ids=rt.points.map(p=>p.id);
  return ids.map(id=>({id,d:Math.hypot(rt.points[id].x-world.x,rt.points[id].z-world.z)})).sort((a,b)=>a.d-b.d).slice(0,count).map(x=>x.id);
}

export function segmentCandidates(world,rt,{limit=10,maxRadiusCells=3}={}){
  let ids=[];
  for(let r=0;r<=maxRadiusCells && ids.length<limit;r++) ids=nearbyBucketValues(rt.segmentBuckets,world,rt.bucketSize,r);
  if(!ids.length) ids=rt.segments.map(s=>s.id);
  const rows=[];
  for(const id of ids){ const s=rt.segments[id],a=rt.points[s.from],b=rt.points[s.to]; const q=project(world,a,b); rows.push({segmentId:id,point:{x:q.x,z:q.z},t:q.t,distanceM:q.distance,bearing:s.bearing}); }
  rows.sort((a,b)=>a.distanceM-b.distanceM);
  return rows.slice(0,limit);
}

export function matchDirectedSegment(world,headingDeg,rt,previousSegmentId=null){
  const candidates=segmentCandidates(world,rt,{limit:30,maxRadiusCells:3});
  let best=null;
  for(const c of candidates){
    const h=Number.isFinite(headingDeg)?angleError(headingDeg,c.bearing):0;
    const continuity=c.segmentId===previousSegmentId?-8:0;
    const score=c.distanceM+h*0.72+continuity;
    if(!best||score<best.score) best={...c,headingErrorDeg:h,score};
  }
  if(!best) return null;
  best.confidence=clamp(1-best.distanceM/95-best.headingErrorDeg/210,0,1);
  return best;
}

function dirtMultiplier(segment){
  const t=(segment.roadType||'').toLowerCase();
  return /dirt|gravel|offroad|off-road|trail/.test(t)?8:1;
}
function heuristic(rt,segmentId,goals){
  const p=rt.points[rt.segments[segmentId].to]; let best=Infinity;
  for(const g of goals){const q=rt.points[g];best=Math.min(best,Math.hypot(q.x-p.x,q.z-p.z));}
  return best;
}
class Heap{
  constructor(){this.a=[];}
  push(item){let i=this.a.length;this.a.push(item);while(i){const p=(i-1)>>1;if(this.a[p][0]<=item[0])break;this.a[i]=this.a[p];i=p;}this.a[i]=item;}
  pop(){if(!this.a.length)return null;const root=this.a[0],last=this.a.pop();if(this.a.length){let i=0;while(true){let l=i*2+1,r=l+1;if(l>=this.a.length)break;let c=r<this.a.length&&this.a[r][0]<this.a[l][0]?r:l;if(this.a[c][0]>=last[0])break;this.a[i]=this.a[c];i=c;}this.a[i]=last;}return root;}
  get length(){return this.a.length;}
}

export function routeFromMatch(match,targetWorld,rt,{avoidDirt=true,maxVisited=100000}={}){
  if(!match||!rt.segments[match.segmentId]) return null;
  const goals=nearestPointIds(targetWorld,rt,1), goalSet=new Set(goals);
  const n=rt.segments.length,dist=new Float64Array(n);dist.fill(Infinity);const prev=new Int32Array(n);prev.fill(-1);const done=new Uint8Array(n);
  const start=match.segmentId,startSeg=rt.segments[start];
  dist[start]=Math.max(0,(1-clamp(match.t,0,1))*startSeg.length)*(avoidDirt?dirtMultiplier(startSeg):1);
  const heap=new Heap();heap.push([dist[start]+heuristic(rt,start,goals),start]);
  let found=-1,visited=0;
  while(heap.length&&visited<maxVisited){const row=heap.pop(),sid=row[1];if(done[sid])continue;done[sid]=1;visited++;const s=rt.segments[sid];if(goalSet.has(s.to)){found=sid;break;}
    for(const nid of rt.next[sid]){if(done[nid])continue;const ns=rt.segments[nid];const nd=dist[sid]+ns.length*(avoidDirt?dirtMultiplier(ns):1);if(nd<dist[nid]){dist[nid]=nd;prev[nid]=sid;heap.push([nd+heuristic(rt,nid,goals),nid]);}}
  }
  if(found<0) return null;
  const ids=[];for(let x=found;x>=0;x=prev[x]){ids.push(x);if(x===start)break;}ids.reverse();if(ids[0]!==start)return null;
  const worldPoints=[{x:match.point.x,z:match.point.z}];let meters=0;
  const first=rt.segments[ids[0]],fp=rt.points[first.to];worldPoints.push({x:fp.x,z:fp.z});meters+=Math.max(0,(1-match.t)*first.length);
  for(let i=1;i<ids.length;i++){const s=rt.segments[ids[i]],p=rt.points[s.to];worldPoints.push({x:p.x,z:p.z});meters+=s.length;}
  return {segmentIds:ids,worldPoints,distanceM:meters,targetPointId:rt.segments[found].to,visited};
}

export function routeBetweenWorldPoints(startWorld,targetWorld,rt,opts={}){
  let best=null;
  const candidates=segmentCandidates(startWorld,rt,{limit:12,maxRadiusCells:3});
  const nearest=candidates.length?candidates[0].distanceM:Infinity;
  for(const c of candidates){
    if(c.distanceM>nearest+25) continue;
    const m={...c,headingErrorDeg:0,confidence:1};const route=routeFromMatch(m,targetWorld,rt,opts);if(!route)continue;const score=route.distanceM+c.distanceM;if(!best||score<best.score)best={...route,score};
  }
  if(!best)return null;delete best.score;return best;
}

export function nextRerouteState(state,{offRoute,confidence,nowMs,confirmMs=800,minConfidence=.45}={}){
  if(!offRoute||!Number.isFinite(confidence)||confidence<minConfidence) return {pendingSince:null,shouldReroute:false};
  const pending=Number.isFinite(state?.pendingSince)?state.pendingSince:nowMs;
  return {pendingSince:pending,shouldReroute:nowMs-pending>=confirmMs};
}

function classify(delta){const a=Math.abs(delta);if(a<20)return null;const direction=delta>0?'right':'left';let kind='keep';if(a>=45)kind='turn';if(a>=120)kind='sharp';if(a>=165)kind='uturn';return {direction,kind};}
export function routeManeuvers(route,pixelPoints,rt){
  const ids=route?.segmentIds||[];if(ids.length<2||pixelPoints.length<3)return[];const cumulative=[0];for(let i=1;i<pixelPoints.length;i++)cumulative[i]=cumulative[i-1]+Math.hypot(pixelPoints[i][0]-pixelPoints[i-1][0],pixelPoints[i][1]-pixelPoints[i-1][1]);
  const out=[];
  for(let i=0;i<ids.length-1;i++){const a=rt.segments[ids[i]],b=rt.segments[ids[i+1]];if(a.to!==b.from)continue;const isJunction=a.sectionId!==b.sectionId||(rt.next[a.id]||[]).length>1;if(!isJunction)continue;const d=signedDelta(bearingPixel(pixelPoints[i],pixelPoints[i+1]),bearingPixel(pixelPoints[i+1],pixelPoints[i+2]));const c=classify(d);if(!c)continue;out.push({pathIndex:i+1,point:pixelPoints[i+1],distanceFromStartPx:cumulative[i+1],deltaDeg:d,...c});}
  return out;
}
