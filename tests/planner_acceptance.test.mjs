import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

import {buildSearchIndex, searchPlaces} from '../static/planner/search.js';
import {interactionForPointer} from '../static/planner/map.js';
import {reorderPreview, canStartNavigation} from '../static/planner/route_editor.js';
import {historyLabel} from '../static/planner/history.js';

const place=(id,name,anchor,tags=[])=>({
  id,name,nav_anchor_point_id:anchor,tags,category:'landmarks',source:'curated',
  default_visible:true,quality:'verified',surface:'asphalt',access:'easy'
});

test('acceptance: search add add reorder then resolved preview enables Start',()=>{
  const places=[place('a','Hakone Nanamagari',1,['mountain','hairpins']),place('b','Daikoku Parking Area',2,['parking','night'])];
  const index=buildSearchIndex(places);
  const a=searchPlaces(index,'hakne',{mode:'recommended'}).results[0];
  const b=searchPlaces(index,'daikoku',{mode:'recommended'}).results[0];
  assert.equal(a.id,'a'); assert.equal(b.id,'b');
  let items=[{id:'i-a',type:'place',place_id:a.id,nav_anchor_point_id:a.nav_anchor_point_id},{id:'i-b',type:'place',place_id:b.id,nav_anchor_point_id:b.nav_anchor_point_id}];
  items=reorderPreview(items,'i-b',0);
  assert.deepEqual(items.map(x=>x.id),['i-b','i-a']);
  assert.equal(canStartNavigation(items,{revision:2,resolved:true}),true);
});

test('acceptance: double click is a temporary waypoint and the mutation is undoable',()=>{
  assert.equal(interactionForPointer({button:0,shiftKey:false,detail:2}),'temporary_waypoint');
  assert.equal(historyLabel('add_item'),'Add place');
  assert.equal(historyLabel('remove_item'),'Remove route item');
});

test('acceptance: unresolved directed leg disables Start rather than falling back',()=>{
  assert.equal(canStartNavigation([{id:'a'}],{revision:1,resolved:false}),false);
  const planner=fs.readFileSync(new URL('../static/planner/planner.js',import.meta.url),'utf8');
  assert.match(planner,/canStartNavigation\s*\(/);
  assert.doesNotMatch(planner,/shortestPath\s*\(/);
});

test('acceptance: PLAN and DRIVE keep live session synchronization wiring',()=>{
  const planner=fs.readFileSync(new URL('../static/planner/planner.js',import.meta.url),'utf8');
  const drive=fs.readFileSync(new URL('../static/app.js',import.meta.url),'utf8');
  assert.match(planner,/navigationStart/);
  assert.match(planner,/navigation\.updated/);
  assert.match(drive,/navigation\.updated/);
  assert.match(drive,/route\.updated/);
});
