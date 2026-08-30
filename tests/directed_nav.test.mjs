import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildDirectedRuntime, matchDirectedSegment, routeFromMatch, routeBetweenWorldPoints,
  nextRerouteState, routeManeuvers
} from '../static/directed_nav.js';

function payload() {
  return {
    format:'fh6-navgraph-v1', capabilities:{directed_segments:true,turn_transitions:true,route_validated:true},
    points:[
      [0,0,0,0],[1,100,0,0],[2,200,0,0],[3,100,0,100],[4,200,0,100],
      [5,0,0,8],[6,100,0,8]
    ],
    // 0->1->2 is one-way east; 1->3->4 is alternate legal continuation; 5->6 opposite parallel carriageway.
    segments:[
      [0,0,0,1,100,1,'asphalt'],[1,0,1,2,100,1,'asphalt'],
      [2,1,1,3,100,0,'asphalt'],[3,1,3,1,100,0,'asphalt'],
      [4,2,3,4,100,0,'asphalt'],[5,2,4,3,100,0,'asphalt'],
      [6,3,6,5,100,1,'asphalt']
    ],
    transitions:[[0,1],[0,2],[2,4],[5,3],[3,1]],
  };
}

test('runtime fails closed unless authoritative capabilities are true',()=>{
  assert.throws(()=>buildDirectedRuntime({...payload(),capabilities:{directed_segments:false}}),/directed/i);
});

test('map matcher prefers heading-compatible directed carriageway over closer opposite direction',()=>{
  const rt=buildDirectedRuntime(payload(),{bucketSize:100});
  const m=matchDirectedSegment({x:50,z:5},90,rt,null);
  assert.equal(m.segmentId,0); // eastbound at z=0; opposite carriageway is z=8 westbound
  assert.ok(m.confidence>0.45);
});

test('one-way reverse traversal is impossible',()=>{
  const rt=buildDirectedRuntime(payload(),{bucketSize:100});
  const start=matchDirectedSegment({x:180,z:0},270,rt,null);
  // there is no westbound segment on 0-1-2, so no legal route back to point 0.
  const route=routeFromMatch(start,{x:0,z:0},rt);
  assert.equal(route,null);
});

test('missed turn reroute continues through legal forward connection',()=>{
  const rt=buildDirectedRuntime(payload(),{bucketSize:100});
  const start=matchDirectedSegment({x:90,z:0},90,rt,null);
  const route=routeFromMatch(start,{x:200,z:100},rt);
  assert.ok(route);
  assert.deepEqual(route.segmentIds,[0,2,4]);
  assert.ok(!route.segmentIds.includes(6));
});

test('routeBetweenWorldPoints chooses a legal start direction',()=>{
  const rt=buildDirectedRuntime(payload(),{bucketSize:100});
  const route=routeBetweenWorldPoints({x:10,z:0},{x:200,z:100},rt);
  assert.ok(route);
  assert.deepEqual(route.segmentIds,[0,2,4]);
});

test('reroute state requires persistent off-route condition and confident match',()=>{
  let s={pendingSince:null};
  s=nextRerouteState(s,{offRoute:true,confidence:.9,nowMs:1000});
  assert.equal(s.shouldReroute,false);
  s=nextRerouteState(s,{offRoute:true,confidence:.9,nowMs:1700});
  assert.equal(s.shouldReroute,false);
  s=nextRerouteState(s,{offRoute:true,confidence:.9,nowMs:1850});
  assert.equal(s.shouldReroute,true);
  s=nextRerouteState(s,{offRoute:false,confidence:.9,nowMs:1900});
  assert.equal(s.pendingSince,null);
});

test('route maneuvers classify a real section change turn',()=>{
  const rt=buildDirectedRuntime(payload(),{bucketSize:100});
  const route={segmentIds:[0,2,4]};
  const pixelPoints=[[0,0],[100,0],[100,-100],[200,-100]];
  const m=routeManeuvers(route,pixelPoints,rt);
  assert.equal(m.length,2);
  assert.equal(m[0].direction,'left');
});
