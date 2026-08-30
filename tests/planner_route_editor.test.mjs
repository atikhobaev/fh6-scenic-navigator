import test from 'node:test'; import assert from 'node:assert/strict';
import { reorderPreview, moveUp, moveDown, canStartNavigation, shouldAcceptPreview, expandedItemModel } from '../static/planner/route_editor.js';
const items=[{id:'a',type:'place'},{id:'b',type:'scenic_road',direction:'forward'},{id:'c',type:'temporary'}];

test('drag preview and arrow reorder are deterministic',()=>{
 assert.deepEqual(reorderPreview(items,'a',2).map(x=>x.id),['b','c','a']);
 assert.deepEqual(moveUp(items,'b').map(x=>x.id),['b','a','c']);
 assert.deepEqual(moveDown(items,'b').map(x=>x.id),['a','c','b']);
});

test('start disabled on unresolved leg and stale preview is discarded',()=>{
 assert.equal(canStartNavigation(items,{resolved:false}),false); assert.equal(canStartNavigation(items,{resolved:true}),true);
 assert.equal(shouldAcceptPreview(9,8),false); assert.equal(shouldAcceptPreview(9,9),true);
});

test('expanded scenic item hides technical via points by default',()=>{
 const m=expandedItemModel({id:'s',type:'scenic_road',direction:'forward'},{scenic_distance_m:1234,point_ids:[1,2,3,4]}); assert.equal(m.hiddenViaCount,2); assert.equal(m.direction,'forward');
});
