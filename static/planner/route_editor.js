export function reorderPreview(items,itemId,target){const a=items.map(x=>({...x}));const i=a.findIndex(x=>x.id===itemId);if(i<0)return a;const [it]=a.splice(i,1);a.splice(Math.max(0,Math.min(target,a.length)),0,it);return a;}
export function moveUp(items,id){const i=items.findIndex(x=>x.id===id);return i>0?reorderPreview(items,id,i-1):items.map(x=>({...x}));}
export function moveDown(items,id){const i=items.findIndex(x=>x.id===id);return i>=0&&i<items.length-1?reorderPreview(items,id,i+1):items.map(x=>({...x}));}
export function canStartNavigation(items,preview){return Boolean(items?.length&&preview?.resolved);}
export function shouldAcceptPreview(currentRevision,resultRevision){return Number(currentRevision)===Number(resultRevision);}
export function expandedItemModel(item,leg={}){const n=Math.max(0,(leg.point_ids?.length||0)-2);return {id:item.id,type:item.type,direction:item.direction||null,hiddenViaCount:n,distance_m:leg.distance_m??null,scenic_distance_m:leg.scenic_distance_m??null};}
export function routeItemLabel(item,placeById=new Map()){if(item.type==='scenic_road'||item.type==='scenic_loop')return item.custom_label||item.scenic_block_id||'Scenic block';if(item.place_id)return placeById.get(item.place_id)?.name||item.place_id;return item.custom_label||'Waypoint';}
