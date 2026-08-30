import test from 'node:test';
import assert from 'node:assert/strict';
import { hubToPixel, worldToPixel, distanceToSegmentPx, pixelsToWorldMeters } from '../static/nav_logic.js';

test('world calibration maps reference A', () => {
  const [x, y] = worldToPixel(-119.49154, 3888.595);
  assert.ok(Math.abs(x - 2089486) < 0.01);
  assert.ok(Math.abs(y - 2087415) < 0.01);
});

test('MapGenie landmark coordinates use WebMercator at max zoom', () => {
  const [x, y] = hubToPixel(0.9135, -0.5634); // Hirosaki Castle
  assert.ok(Math.abs(x - 2090587.91424) < 0.01);
  assert.ok(Math.abs(y - 2086508.5026647933) < 0.01);
});

test('distance to segment works', () => {
  assert.equal(distanceToSegmentPx([5, 4], [0, 0], [10, 0]), 4);
});

test('pixel distance converts to game world meters', () => {
  assert.ok(Math.abs(pixelsToWorldMeters(37.23) - 100) < 0.2);
});

import { nearestWaypointIndex, maybeAdvanceWaypoint } from '../static/nav_logic.js';

test('nearest waypoint finds closest point', () => {
  const pts = [[0,0],[100,0],[200,0]];
  assert.equal(nearestWaypointIndex([122, 3], pts), 1);
});

test('waypoint advances when within reach radius', () => {
  const pts = [[0,0],[100,0],[200,0]];
  assert.equal(maybeAdvanceWaypoint([98, 0], pts, 1, 10), 2);
  assert.equal(maybeAdvanceWaypoint([50, 0], pts, 1, 10), 1);
});

import * as navLogic from '../static/nav_logic.js';

test('loop navigation appends the starting POI as the final target', () => {
  assert.equal(typeof navLogic.withLoopClosure, 'function');
  const src = [{name:'Start',game:'Start',lat:1,lng:2},{name:'B',game:'B',lat:3,lng:4}];
  const loop = navLogic.withLoopClosure(src);
  assert.equal(loop.length, 3);
  assert.equal(loop[2].game, 'Start');
  assert.equal(loop[2].loopClosure, true);
  assert.notEqual(loop[2], src[0]);
});

test('directional loop keeps Hirosaki anchored and reverses the interior itinerary', async () => {
  const {buildDirectionalLoop} = await import('../static/nav_logic.js');
  const src = [
    {name:'H',game:'Hirosaki Castle'},
    {name:'A',game:'A'},
    {name:'B',game:'B'},
    {name:'C',game:'C'},
  ];
  const f = buildDirectionalLoop(src, 'forward');
  const r = buildDirectionalLoop(src, 'reverse');
  assert.deepEqual(f.map(w=>w.game), ['Hirosaki Castle','A','B','C','Hirosaki Castle']);
  assert.deepEqual(r.map(w=>w.game), ['Hirosaki Castle','C','B','A','Hirosaki Castle']);
  assert.equal(r.at(-1).loopClosure, true);
});


test('loop waypoint advancement continues from final Hirosaki closure to the first scenic stop', async () => {
  const {maybeAdvanceLoopWaypoint} = await import('../static/nav_logic.js');
  assert.equal(typeof maybeAdvanceLoopWaypoint, 'function');
  const pts = [[0,0],[100,0],[0,0]]; // start, scenic stop, loop closure at start
  assert.equal(maybeAdvanceLoopWaypoint([0,0], pts, 2, 10, true), 1);
  assert.equal(maybeAdvanceLoopWaypoint([0,0], pts, 2, 10, false), 2);
});

test('virtual zoom 15 reuses zoom 14 tiles at double display scale', async () => {
  const {tileDisplayPlan} = await import('../static/nav_logic.js');
  assert.equal(typeof tileDisplayPlan, 'function');
  assert.deepEqual(tileDisplayPlan(15, 14), {sourceZoom:14, displayScale:2});
  assert.deepEqual(tileDisplayPlan(14, 14), {sourceZoom:14, displayScale:1});
  assert.deepEqual(tileDisplayPlan(12, 14), {sourceZoom:12, displayScale:1});
});

test('auto zoom engages below 40 kmh and remembers previous zoom', async () => {
  const {nextAutoZoomState} = await import('../static/nav_logic.js');
  assert.equal(typeof nextAutoZoomState, 'function');
  const state = nextAutoZoomState({speedKmh:39, follow:true, zoom:12, active:false, savedZoom:null, maxZoom:15});
  assert.deepEqual(state, {zoom:15, active:true, savedZoom:12});
});

test('auto zoom holds through 40-45 kmh hysteresis and restores above 45', async () => {
  const {nextAutoZoomState} = await import('../static/nav_logic.js');
  const held = nextAutoZoomState({speedKmh:43, follow:true, zoom:15, active:true, savedZoom:11, maxZoom:15});
  assert.deepEqual(held, {zoom:15, active:true, savedZoom:11});
  const released = nextAutoZoomState({speedKmh:46, follow:true, zoom:15, active:true, savedZoom:11, maxZoom:15});
  assert.deepEqual(released, {zoom:11, active:false, savedZoom:null});
});

test('auto zoom does not engage when follow mode is off', async () => {
  const {nextAutoZoomState} = await import('../static/nav_logic.js');
  const state = nextAutoZoomState({speedKmh:10, follow:false, zoom:12, active:false, savedZoom:null, maxZoom:15});
  assert.deepEqual(state, {zoom:12, active:false, savedZoom:null});
});

test('turn alert level escalates at 500, 300 and 100 meters', async () => {
  const {turnAlertLevel} = await import('../static/nav_logic.js');
  assert.equal(typeof turnAlertLevel, 'function');
  assert.equal(turnAlertLevel(501), 'none');
  assert.equal(turnAlertLevel(500), 'far');
  assert.equal(turnAlertLevel(301), 'far');
  assert.equal(turnAlertLevel(300), 'near');
  assert.equal(turnAlertLevel(101), 'near');
  assert.equal(turnAlertLevel(100), 'urgent');
  assert.equal(turnAlertLevel(0), 'urgent');
});

test('low zoom reuses z11 source tiles instead of requesting blocked z9 and z10 tiles',()=>{
  assert.deepEqual(navLogic.tileDisplayPlan(9,14),{sourceZoom:11,displayScale:0.25});
  assert.deepEqual(navLogic.tileDisplayPlan(10,14),{sourceZoom:11,displayScale:0.5});
  assert.deepEqual(navLogic.tileDisplayPlan(11,14),{sourceZoom:11,displayScale:1});
});

test('FH6 tile bounds clamp low zoom source requests to the actual map extent',()=>{
  assert.deepEqual(navLogic.tileValidRange(14,14),[8128,8191]);
  assert.deepEqual(navLogic.tileValidRange(11,14),[1016,1023]);
});
