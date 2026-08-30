import test from 'node:test';
import assert from 'node:assert/strict';
import {LAYER_REGISTRY} from '../static/planner/layers.js';
import {iconSpec, iconMarkup} from '../static/planner/icons.js';
import {plannerTileDisplayPlan, plannerTileSourceRange, placeMarkerCandidates} from '../static/planner/map.js';

test('every planner layer uses a font-independent SVG icon id',()=>{
  for(const layer of Object.values(LAYER_REGISTRY)){
    assert.match(layer.icon,/^[a-z0-9_-]+$/,`${layer.id} should use semantic icon id`);
    const spec=iconSpec(layer.icon);
    assert.ok(spec,`missing SVG spec for ${layer.id}:${layer.icon}`);
    assert.ok(Array.isArray(spec.shapes)&&spec.shapes.length>0,`empty SVG spec for ${layer.icon}`);
    const markup=iconMarkup(layer.icon);
    assert.match(markup,/^<svg\b/);
    assert.doesNotMatch(markup,/[⌁〰◆▣⌂⚑≈↝➜⌑◇▧☺◎●•]/);
  }
});

test('key categories get recognizable distinct SVG icon families',()=>{
  assert.equal(LAYER_REGISTRY.scenic_spots.icon,'mountain');
  assert.equal(LAYER_REGISTRY.settlements.icon,'home');
  assert.equal(LAYER_REGISTRY.landmarks.icon,'landmark');
  assert.equal(LAYER_REGISTRY.photo_spots.icon,'camera');
  assert.equal(LAYER_REGISTRY.scenic_roads.icon,'road');
  assert.equal(LAYER_REGISTRY.speed_traps.icon,'speedometer');
  assert.equal(LAYER_REGISTRY.danger_signs.icon,'warning');
  assert.equal(LAYER_REGISTRY.barn_finds.icon,'barn');
});

test('selected ordinary place keeps its icon marker and is excluded from clustering',()=>{
  const places=[
    {id:'selected',source:'curated',category:'scenic_place',position:{x:0,z:0}},
    {id:'normal',source:'game',category:'landmark',position:{x:1,z:1}},
    {id:'route',source:'game',category:'landmark',position:{x:2,z:2}},
  ];
  const out=placeMarkerCandidates(places,new Set(['route']),'selected');
  assert.deepEqual(out.map(x=>x.p.id),['selected','normal']);
  const selected=out.find(x=>x.p.id==='selected');
  assert.equal(selected.visual.state,'selected');
  assert.equal(selected.visual.icon,'mountain');
  assert.equal(selected.visual.clusterable,false);
});

test('planner low zoom reuses z11 tiles and scales them down in browser',()=>{
  assert.deepEqual(plannerTileDisplayPlan(9),{sourceZoom:11,displayScale:0.25});
  assert.deepEqual(plannerTileDisplayPlan(10),{sourceZoom:11,displayScale:0.5});
  assert.deepEqual(plannerTileDisplayPlan(11),{sourceZoom:11,displayScale:1});
  assert.deepEqual(plannerTileDisplayPlan(12),{sourceZoom:12,displayScale:1});
  for(let z=9;z<=14;z++)assert.ok(plannerTileDisplayPlan(z).sourceZoom>=11);
  assert.deepEqual(plannerTileSourceRange(9),[1016,1023]);
  assert.deepEqual(plannerTileSourceRange(10),[1016,1023]);
});
