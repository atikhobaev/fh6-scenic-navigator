import {routeFromMatch} from './directed_nav.js';

export function plannerProgressModel(snapshot){
  const by=new Map((snapshot?.progress||[]).map(p=>[p.route_item_id,p]));
  return (snapshot?.route?.items||[]).map((item,index)=>({item,index,status:by.get(item.id)?.status||'upcoming'}));
}

function exactRemainingFromMatch(match,fixed,rt){
  const idx=fixed.indexOf(match.segmentId); if(idx<0)return null;
  const ids=fixed.slice(idx),first=rt.segments[ids[0]]; if(!first)return null;
  const worldPoints=[{x:match.point.x,z:match.point.z},{x:rt.points[first.to].x,z:rt.points[first.to].z}];
  let distanceM=Math.max(0,(1-match.t)*first.length);
  for(let i=1;i<ids.length;i++){const s=rt.segments[ids[i]];if(!s)return null;worldPoints.push({x:rt.points[s.to].x,z:rt.points[s.to].z});distanceM+=s.length;}
  return {segmentIds:ids,worldPoints,distanceM,targetPointId:rt.segments[ids.at(-1)].to};
}

export function plannerGuidanceFromMatch(match,snapshot,rt,{avoidDirt=true}={}){
  const target=snapshot?.current_target;if(!match||!target)return null;
  const fixed=(target.fixed_segment_ids||[]).map(Number);
  if(fixed.length){
    const inside=exactRemainingFromMatch(match,fixed,rt);if(inside)return inside;
    const entry=target.entry_world;if(!entry)return null;
    const approach=routeFromMatch(match,{x:entry.x,z:entry.z},rt,{avoidDirt});if(!approach)return null;
    const worldPoints=[...approach.worldPoints],segmentIds=[...approach.segmentIds];let distanceM=approach.distanceM;
    for(const sid of fixed){
      if(segmentIds.at(-1)===sid)continue;
      const s=rt.segments[sid];if(!s)return null;
      const last=worldPoints.at(-1),from=rt.points[s.from];
      if(last&&Math.hypot(last.x-from.x,last.z-from.z)>2)return null;
      segmentIds.push(sid);worldPoints.push({x:rt.points[s.to].x,z:rt.points[s.to].z});distanceM+=s.length;
    }
    return {segmentIds,worldPoints,distanceM,targetPointId:rt.segments[segmentIds.at(-1)].to};
  }
  return routeFromMatch(match,{x:target.world.x,z:target.world.z},rt,{avoidDirt});
}

export function shouldCompletePlannerItem({distanceM,matchSegmentId,guidance}){
  return Number.isFinite(distanceM)&&distanceM<=50&&Number.isInteger(matchSegmentId)&&Boolean(guidance?.segmentIds?.includes(matchSegmentId));
}
