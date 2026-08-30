import test from 'node:test';
import assert from 'node:assert/strict';
import {
  LAYER_GROUPS,LAYER_REGISTRY,recommendedLayerIds,allLayerIds,normalizeLayerState,
  layerForPlace,isPlaceVisible,applyLayerPreset,setAllGroupsCollapsed,serializeLayerState
} from '../static/planner/layers.js';

test('layer registry exposes complete map-first taxonomy',()=>{
  assert.deepEqual(LAYER_GROUPS.map(g=>g.id),['discover','gameplay','pr_stunts','events','races','collect_cars','community','my']);
  for(const id of ['settlements','landmarks','scenic_spots','scenic_roads','photo_spots','houses','festival_sites','easter_eggs','speed_traps','speed_zones','danger_signs','drift_zones','trailblazers','street_races','road_races','touge_races','rally_races','cross_country_races','barn_finds','treasure_cars','boards','collectibles','community_scenic','community_secret_roads','community_jumps','my_places']){
    assert.ok(LAYER_REGISTRY[id],`missing ${id}`);
  }
});

test('recommended preset is calm but keeps discovery layers enabled',()=>{
  const ids=new Set(recommendedLayerIds());
  for(const id of ['settlements','landmarks','scenic_spots','scenic_roads','photo_spots','my_places'])assert.equal(ids.has(id),true,id);
  for(const id of ['barn_finds','treasure_cars','speed_traps','street_races','collectibles'])assert.equal(ids.has(id),false,id);
});

test('layer state normalizes persisted values and supports bulk presets',()=>{
  const normalized=normalizeLayerState({enabled:['landmarks','bogus','barn_finds']});
  assert.deepEqual([...normalized.enabled].sort(),['barn_finds','landmarks']);
  assert.equal(applyLayerPreset(normalized,'all').enabled.size,allLayerIds().length);
  assert.equal(applyLayerPreset(normalized,'none').enabled.size,0);
  assert.deepEqual([...applyLayerPreset(normalized,'recommended').enabled].sort(),[...recommendedLayerIds()].sort());
});

test('place categories map into the central layer registry',()=>{
  assert.equal(layerForPlace({source:'game',category:'barn_find'}).id,'barn_finds');
  assert.equal(layerForPlace({source:'curated',category:'scenic_places'}).id,'scenic_spots');
  assert.equal(layerForPlace({source:'community',category:'secret_road'}).id,'community_secret_roads');
  assert.equal(layerForPlace({source:'user',category:'my_place'}).id,'my_places');
  assert.equal(layerForPlace({source:'game',category:'road_race'}).id,'road_races');
});

test('active route selected and temporary search reveal override hidden layers',()=>{
  const place={id:'p1',source:'game',category:'barn_find'};
  const state={enabled:new Set(['landmarks'])};
  assert.equal(isPlaceVisible(place,state,{}),false);
  assert.equal(isPlaceVisible(place,state,{routePlaceIds:new Set(['p1'])}),true);
  assert.equal(isPlaceVisible(place,state,{selectedId:'p1'}),true);
  assert.equal(isPlaceVisible(place,state,{searchRevealId:'p1'}),true);
});


test('collapsed groups survive repeated normalization and can be collapsed or expanded together',()=>{
  const first=normalizeLayerState({collapsed:['discover','events']});
  assert.deepEqual([...first.collapsed].sort(),['discover','events']);
  const second=normalizeLayerState(first);
  assert.deepEqual([...second.collapsed].sort(),['discover','events']);
  second.collapsed.add('races');
  const restored=normalizeLayerState(serializeLayerState(second));
  assert.deepEqual([...restored.collapsed].sort(),['discover','events','races']);
  const all=setAllGroupsCollapsed(restored,true);
  assert.deepEqual([...all.collapsed].sort(),LAYER_GROUPS.map(g=>g.id).sort());
  const expanded=setAllGroupsCollapsed(all,false);
  assert.equal(expanded.collapsed.size,0);
});
