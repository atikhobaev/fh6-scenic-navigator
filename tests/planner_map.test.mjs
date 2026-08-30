import test from 'node:test'; import assert from 'node:assert/strict';
import { interactionForPointer, clusterMarkers, routeMarkerModel } from '../static/planner/map.js';

test('map semantics follow approved click double-click right-click and shift-click rules',()=>{
 assert.equal(interactionForPointer({button:0,detail:1,shiftKey:false}),'select');
 assert.equal(interactionForPointer({button:0,detail:2,shiftKey:false}),'temporary_waypoint');
 assert.equal(interactionForPointer({button:2,detail:1,shiftKey:false}),'context_menu');
 assert.equal(interactionForPointer({button:0,detail:1,shiftKey:true}),'quick_add');
});

test('route markers are never clustered with library markers',()=>{
 const clusters=clusterMarkers([{id:'a',x:10,y:10},{id:'b',x:12,y:11}],40); assert.equal(clusters.length,1);
 const route=routeMarkerModel([{id:'x'},{id:'y'}]); assert.deepEqual(route.map(x=>x.number),[1,2]); assert.ok(route.every(x=>x.clusterable===false));
});

import { shouldPromotePointerToPan } from '../static/planner/map.js';

test('marker pointer becomes map pan only after 5px threshold',()=>{
 assert.equal(shouldPromotePointerToPan({x:100,y:100},103,104),false);
 assert.equal(shouldPromotePointerToPan({x:100,y:100},106,100),true);
});

import fs from 'node:fs';
const mapSource=fs.readFileSync(new URL('../static/planner/map.js',import.meta.url),'utf8');

test('context menu closes when pointer is pressed anywhere outside it',()=>{
 assert.match(mapSource,/document\.addEventListener\(['"]pointerdown['"][\s\S]{0,700}closeContext\(\)/);
});

test('marker selection is resolved from pointer gesture instead of fragile click after pointer capture',()=>{
 assert.match(mapSource,/drag\.(?:place|targetPlace|placeId)/);
 assert.match(mapSource,/pointerup[\s\S]{0,1200}onSelect/);
});
