const def=(id,group,label,icon,defaults=false,categories=[],opts={})=>({id,group,label,labelKey:`layer.${id}`,icon,defaultVisible:defaults,categories,cluster:opts.cluster!==false,priority:opts.priority||0});

export const LAYER_REGISTRY={
  settlements:def('settlements','discover','Settlements','home',true,['settlement','city','town','village']),
  landmarks:def('landmarks','discover','Landmarks','landmark',true,['landmark']),
  scenic_spots:def('scenic_spots','discover','Scenic Spots','mountain',true,['scenic_place','scenic_places','scenic_spot']),
  scenic_roads:def('scenic_roads','discover','Scenic Roads','road',true,['scenic_road','scenic_roads'],{cluster:false,priority:3}),
  photo_spots:def('photo_spots','discover','Photo Spots','camera',true,['photo_spot','photography','photo']),
  houses:def('houses','discover','Houses','home',false,['house','houses']),
  festival_sites:def('festival_sites','discover','Festival Sites','festival',false,['festival','festival_site','horizon_festival']),
  easter_eggs:def('easter_eggs','discover','Easter Eggs','egg',false,['easter_egg']),
  other_discovery:def('other_discovery','discover','Other Discovery','pin',false,['discovery','other_discovery']),

  story:def('story','gameplay','Story / Horizon','book',false,['story','horizon_story','day_trip']),
  yuji_auto:def('yuji_auto','gameplay',"Yuji's Auto",'car',false,['yuji_auto']),
  moto_auto_zine:def('moto_auto_zine','gameplay','Moto Auto Zine','magazine',false,['moto_auto_zine']),
  drift_club:def('drift_club','gameplay','Drift Club Japan','drift',false,['drift_club']),
  raku_raku:def('raku_raku','gameplay','Raku Raku Job','briefcase',false,['raku_raku_job']),
  showcases:def('showcases','gameplay','Showcases','star',false,['showcase','wrist_band']),

  speed_traps:def('speed_traps','pr_stunts','Speed Traps','speedometer',false,['speed_trap']),
  speed_zones:def('speed_zones','pr_stunts','Speed Zones','speed_zone',false,['speed_zone']),
  danger_signs:def('danger_signs','pr_stunts','Danger Signs','warning',false,['danger_sign']),
  drift_zones:def('drift_zones','pr_stunts','Drift Zones','drift',false,['drift_zone']),
  trailblazers:def('trailblazers','pr_stunts','Trailblazers','trailblazer',false,['trailblazer']),

  car_meets:def('car_meets','events','Car Meets','car_group',false,['car_meet']),
  drag_meetups:def('drag_meetups','events','Drag Meetups','drag',false,['drag_meetup']),
  time_attack:def('time_attack','events','Time Attack','stopwatch',false,['time_attack','time_attack_track']),
  world_events:def('world_events','events','World Events','spark',false,['event','world_event']),

  street_races:def('street_races','races','Street Race','race_flag',false,['street_race']),
  road_races:def('road_races','races','Road Race','race_flag',false,['road_race']),
  touge_races:def('touge_races','races','Touge Race','race_mountain',false,['touge_race']),
  drag_races:def('drag_races','races','Drag Race','drag',false,['drag_race']),
  rally_races:def('rally_races','races','Rally Race','rally',false,['rally_race']),
  cross_country_races:def('cross_country_races','races','Cross Country','cross_country',false,['cross_country_race']),

  barn_finds:def('barn_finds','collect_cars','Barn Finds','barn',false,['barn_find']),
  treasure_cars:def('treasure_cars','collect_cars','Treasure Cars','treasure',false,['treasure_car']),
  used_cars:def('used_cars','collect_cars','Used Cars','car',false,['used_car']),
  boards:def('boards','collect_cars','Bonus / XP Boards','board',false,['bonus_board','xp_board','board']),
  collectibles:def('collectibles','collect_cars','Collectibles','collectible',false,['collectible']),
  mascots:def('mascots','collect_cars','Mascots / Characters','mascot',false,['mascot','character']),

  community_scenic:def('community_scenic','community','Community Scenic','mountain',false,['scenic_spot','scenic_place']),
  community_secret_roads:def('community_secret_roads','community','Secret Roads','road',false,['secret_road'],{cluster:false}),
  community_jumps:def('community_jumps','community','Jumps','jump',false,['jump']),
  community_easter_eggs:def('community_easter_eggs','community','Easter Eggs','egg',false,['easter_egg']),
  community_collectibles:def('community_collectibles','community','Collectibles','collectible',false,['collectible']),
  community_other:def('community_other','community','Other','pin',false,['other']),

  my_places:def('my_places','my','My Places','star',true,['my_place'],{priority:4}),
};

export const LAYER_GROUPS=[
  {id:'discover',label:'DISCOVER',labelKey:'group.discover',layers:['settlements','landmarks','scenic_spots','scenic_roads','photo_spots','houses','festival_sites','easter_eggs','other_discovery']},
  {id:'gameplay',label:'GAMEPLAY / STORY',labelKey:'group.gameplay',layers:['story','yuji_auto','moto_auto_zine','drift_club','raku_raku','showcases']},
  {id:'pr_stunts',label:'PR STUNTS',labelKey:'group.pr_stunts',layers:['speed_traps','speed_zones','danger_signs','drift_zones','trailblazers']},
  {id:'events',label:'EVENTS',labelKey:'group.events',layers:['car_meets','drag_meetups','time_attack','world_events']},
  {id:'races',label:'RACES',labelKey:'group.races',layers:['street_races','road_races','touge_races','drag_races','rally_races','cross_country_races']},
  {id:'collect_cars',label:'COLLECT / CARS',labelKey:'group.collect_cars',layers:['barn_finds','treasure_cars','used_cars','boards','collectibles','mascots']},
  {id:'community',label:'COMMUNITY',labelKey:'group.community',layers:['community_scenic','community_secret_roads','community_jumps','community_easter_eggs','community_collectibles','community_other']},
  {id:'my',label:'MY',labelKey:'group.my',layers:['my_places']},
];

const CATEGORY_TO_LAYER=new Map();
for(const layer of Object.values(LAYER_REGISTRY))for(const category of layer.categories)if(!CATEGORY_TO_LAYER.has(category))CATEGORY_TO_LAYER.set(category,layer.id);

export function allLayerIds(){return Object.keys(LAYER_REGISTRY)}
export function recommendedLayerIds(){return Object.values(LAYER_REGISTRY).filter(x=>x.defaultVisible).map(x=>x.id)}

export function normalizeLayerState(raw={}){
  const valid=new Set(allLayerIds());
  let values=raw?.enabled;
  if(values instanceof Set)values=[...values];
  if(!Array.isArray(values))values=recommendedLayerIds();
  let collapsed=raw?.collapsed;
  if(collapsed instanceof Set)collapsed=[...collapsed];
  return {
    enabled:new Set(values.filter(id=>valid.has(id))),
    collapsed:new Set(Array.isArray(collapsed)?collapsed.filter(id=>LAYER_GROUPS.some(g=>g.id===id)):[]),
  };
}
export function serializeLayerState(state){return {enabled:[...(state?.enabled||[])],collapsed:[...(state?.collapsed||[])]}}
export function setAllGroupsCollapsed(state,collapsed=true){
  const next=normalizeLayerState(state);
  next.collapsed=collapsed?new Set(LAYER_GROUPS.map(group=>group.id)):new Set();
  return next;
}
export function applyLayerPreset(state,preset){
  const next=normalizeLayerState(state);
  if(preset==='all')next.enabled=new Set(allLayerIds());
  else if(preset==='none')next.enabled=new Set();
  else next.enabled=new Set(recommendedLayerIds());
  return next;
}
export function toggleLayer(state,id,on=null){
  const next=normalizeLayerState(state),value=on==null?!next.enabled.has(id):Boolean(on);
  if(value)next.enabled.add(id);else next.enabled.delete(id);return next;
}
export function toggleGroup(state,groupId,on=null){
  const next=normalizeLayerState(state),group=LAYER_GROUPS.find(g=>g.id===groupId);if(!group)return next;
  const value=on==null?!group.layers.every(id=>next.enabled.has(id)):Boolean(on);
  for(const id of group.layers)value?next.enabled.add(id):next.enabled.delete(id);return next;
}
export function layerForPlace(place={}){
  if(place.source==='user')return LAYER_REGISTRY.my_places;
  const category=String(place.category||'').toLowerCase();
  if(place.source==='community'){
    const cm={scenic_spot:'community_scenic',scenic_place:'community_scenic',secret_road:'community_secret_roads',jump:'community_jumps',easter_egg:'community_easter_eggs',collectible:'community_collectibles',other:'community_other'};
    return LAYER_REGISTRY[cm[category]||'community_other'];
  }
  const id=CATEGORY_TO_LAYER.get(category);
  if(id)return LAYER_REGISTRY[id];
  if(place.source==='curated')return LAYER_REGISTRY.scenic_spots;
  return LAYER_REGISTRY.other_discovery;
}
export function isPlaceVisible(place,state,context={}){
  if(!place)return false;
  if(context.routePlaceIds?.has?.(place.id)||context.selectedId===place.id||context.searchRevealId===place.id)return true;
  const normalized=state?.enabled instanceof Set?state:normalizeLayerState(state);
  return normalized.enabled.has(layerForPlace(place).id);
}
export function layerCounts(places,state,context={}){
  const counts=Object.fromEntries(allLayerIds().map(id=>[id,0]));
  for(const p of places||[])counts[layerForPlace(p).id]++;
  return counts;
}
