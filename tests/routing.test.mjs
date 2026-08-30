import test from 'node:test';
import assert from 'node:assert/strict';

let routing = {};
try {
  routing = await import('../static/routing.js');
} catch {
  routing = {};
}

test('routing module exposes road graph functions', () => {
  assert.equal(typeof routing.labToMapPixel, 'function');
  assert.equal(typeof routing.buildRoadGraph, 'function');
  assert.equal(typeof routing.routeThroughWaypoints, 'function');
});

test('Labs road-image coordinates map into MapGenie z14 pixels', () => {
  const [x, y] = routing.labToMapPixel(0, 0);
  assert.ok(Math.abs(x - 2086251.73) < 0.01);
  assert.ok(Math.abs(y - 2085126.0044) < 0.01);
});

test('road graph routes only along connected road points', () => {
  const roads = [
    {type:'asphalt', points:[{x:0,y:0},{x:10,y:0},{x:20,y:0}]},
    {type:'asphalt', points:[{x:20,y:0},{x:20,y:10},{x:20,y:20}]},
  ];
  const graph = routing.buildRoadGraph(roads);
  const start = routing.labToMapPixel(0, 0);
  const end = routing.labToMapPixel(20, 20);
  const result = routing.routeThroughWaypoints([start, end], graph, {loop:false});
  assert.equal(result.legs.length, 1);
  assert.ok(result.points.length >= 5);
  assert.deepEqual(result.points[0], graph.nodes[result.waypointNodeIds[0]].pixel);
  assert.deepEqual(result.points.at(-1), graph.nodes[result.waypointNodeIds[1]].pixel);
});

test('loop route returns to the snapped starting road node', () => {
  const roads = [
    {type:'asphalt', points:[{x:0,y:0},{x:10,y:0},{x:20,y:0}]},
    {type:'asphalt', points:[{x:20,y:0},{x:20,y:10},{x:20,y:20}]},
    {type:'asphalt', points:[{x:20,y:20},{x:10,y:20},{x:0,y:20}]},
    {type:'asphalt', points:[{x:0,y:20},{x:0,y:10},{x:0,y:0}]},
  ];
  const graph = routing.buildRoadGraph(roads);
  const a = routing.labToMapPixel(0, 0);
  const b = routing.labToMapPixel(20, 20);
  const result = routing.routeThroughWaypoints([a, b], graph, {loop:true});
  assert.equal(result.legs.length, 2);
  assert.deepEqual(result.points[0], result.points.at(-1));
});

test('route guidance snaps to current leg and looks ahead along the road', () => {
  assert.equal(typeof routing.nearestPolylineProgress, 'function');
  assert.equal(typeof routing.pointAheadOnPolyline, 'function');
  const line = [[0,0],[100,0],[100,100]];
  const progress = routing.nearestPolylineProgress([30,10], line);
  assert.equal(progress.segmentIndex, 0);
  assert.ok(Math.abs(progress.point[0] - 30) < 0.01);
  assert.ok(Math.abs(progress.point[1]) < 0.01);
  const ahead = routing.pointAheadOnPolyline(line, progress, 100);
  assert.ok(Math.abs(ahead[0] - 100) < 0.01);
  assert.ok(Math.abs(ahead[1] - 30) < 0.01);
});

test('remaining route distance follows bends instead of straight-line distance', () => {
  assert.equal(typeof routing.remainingPolylineDistancePx, 'function');
  const line = [[0,0],[100,0],[100,100]];
  const progress = routing.nearestPolylineProgress([30,0], line);
  assert.ok(Math.abs(routing.remainingPolylineDistancePx(line, progress) - 170) < 0.01);
});

test('avoid-dirt routing takes any all-asphalt detour before a shorter dirt shortcut', () => {
  const roads = [
    {type:'dirt', points:[{x:0,y:0},{x:10,y:0}]},
    {type:'asphalt', points:[{x:0,y:0},{x:0,y:10},{x:10,y:10},{x:10,y:0}]},
  ];
  const graph = routing.buildRoadGraph(roads);
  const start = graph.nodes.find(n => n.x === 0 && n.y === 0).id;
  const end = graph.nodes.find(n => n.x === 10 && n.y === 0).id;
  const path = routing.shortestPath(start, end, graph, {avoidDirt:true});
  assert.equal(path.length, 4, `expected asphalt detour, got ${path.join(' -> ')}`);
});

test('avoid-dirt routing falls back to dirt when asphalt cannot connect the endpoints', () => {
  const roads = [
    {type:'asphalt', points:[{x:0,y:0},{x:5,y:0}]},
    {type:'dirt', points:[{x:5,y:0},{x:10,y:0}]},
  ];
  const graph = routing.buildRoadGraph(roads);
  const start = graph.nodes.find(n => n.x === 0 && n.y === 0).id;
  const end = graph.nodes.find(n => n.x === 10 && n.y === 0).id;
  const path = routing.shortestPath(start, end, graph, {avoidDirt:true});
  assert.equal(path.length, 3);
  assert.deepEqual(path.map(id => [graph.nodes[id].x, graph.nodes[id].y]), [[0,0],[5,0],[10,0]]);
});

test('turn detection emits a right turn at a real graph junction and ignores straight junctions', () => {
  assert.equal(typeof routing.detectManeuvers, 'function');
  const roads = [
    {type:'asphalt', points:[{x:0,y:0},{x:10,y:0},{x:10,y:10}]},
    {type:'asphalt', points:[{x:10,y:0},{x:20,y:0}]},
    {type:'asphalt', points:[{x:10,y:10},{x:20,y:10}]},
  ];
  const graph = routing.buildRoadGraph(roads);
  const nodeIds = [
    graph.nodes.find(n => n.x === 0 && n.y === 0).id,
    graph.nodes.find(n => n.x === 10 && n.y === 0).id,
    graph.nodes.find(n => n.x === 10 && n.y === 10).id,
  ];
  const maneuvers = routing.detectManeuvers(nodeIds, graph, {lookDistancePx:1, minTurnDeg:20});
  assert.equal(maneuvers.length, 1);
  assert.equal(maneuvers[0].direction, 'right');
  assert.equal(maneuvers[0].kind, 'turn');
});

test('nextManeuver reports route distance from current polyline progress', () => {
  assert.equal(typeof routing.nextManeuver, 'function');
  const points = [[0,0],[100,0],[100,100]];
  const maneuvers = [{pathIndex:1, point:[100,0], distanceFromStartPx:100, direction:'right', kind:'turn'}];
  const progress = routing.nearestPolylineProgress([25,0], points);
  const next = routing.nextManeuver(maneuvers, points, progress);
  assert.ok(next);
  assert.ok(Math.abs(next.distancePx - 75) < 0.001);
  const after = routing.nearestPolylineProgress([100,40], points);
  assert.equal(routing.nextManeuver(maneuvers, points, after), null);
});

test('routeThroughWaypoints uses avoid-dirt behavior by default', () => {
  const roads = [
    {type:'dirt', points:[{x:0,y:0},{x:10,y:0}]},
    {type:'asphalt', points:[{x:0,y:0},{x:0,y:10},{x:10,y:10},{x:10,y:0}]},
  ];
  const graph = routing.buildRoadGraph(roads);
  const start = routing.labToMapPixel(0, 0);
  const end = routing.labToMapPixel(10, 0);
  const route = routing.routeThroughWaypoints([start,end],graph,{loop:false});
  assert.equal(route.legs[0].nodeIds.length, 4);
});

test('turn detection does not announce a straight-through junction', () => {
  const roads = [
    {type:'asphalt', points:[{x:0,y:0},{x:10,y:0},{x:20,y:0}]},
    {type:'asphalt', points:[{x:10,y:0},{x:10,y:10}]},
  ];
  const graph = routing.buildRoadGraph(roads);
  const nodeIds = [
    graph.nodes.find(n => n.x === 0 && n.y === 0).id,
    graph.nodes.find(n => n.x === 10 && n.y === 0).id,
    graph.nodes.find(n => n.x === 20 && n.y === 0).id,
  ];
  assert.deepEqual(routing.detectManeuvers(nodeIds, graph, {lookDistancePx:1}), []);
});

test('through-asphalt waypoint snapping avoids a closer dead-end node', () => {
  assert.equal(typeof routing.nearestSuitableRoadNode, 'function');
  const roads = [
    {type:'asphalt', points:[{x:0,y:0},{x:10,y:0},{x:20,y:0}]},
    {type:'asphalt', points:[{x:10,y:0},{x:10,y:10}]},
  ];
  const graph = routing.buildRoadGraph(roads);
  const deadEndPixel = routing.labToMapPixel(10, 10);
  const result = routing.nearestSuitableRoadNode(deadEndPixel, graph, {surface:'asphalt', minDegree:2});
  assert.equal(graph.nodes[result.id].x, 10);
  assert.equal(graph.nodes[result.id].y, 0);
});

test('loop routing penalizes reused edges and takes a different return corridor when available', () => {
  const roads = [
    {type:'asphalt', points:[{x:0,y:0},{x:10,y:0},{x:20,y:0}]},
    {type:'asphalt', points:[{x:0,y:0},{x:0,y:10},{x:20,y:10},{x:20,y:0}]},
  ];
  const graph = routing.buildRoadGraph(roads);
  const a = routing.labToMapPixel(0,0);
  const b = routing.labToMapPixel(20,0);
  const result = routing.routeThroughWaypoints([a,b], graph, {loop:true, avoidDirt:true, reusePenalty:8, avoidImmediateBacktrack:true});
  assert.equal(result.legs.length, 2);
  assert.equal(result.legs[0].nodeIds.length, 3, 'outbound should use short direct road');
  assert.equal(result.legs[1].nodeIds.length, 4, 'return should use unused outer corridor');
});


test('remainingPolylinePoints returns only the untravelled route from current projection', () => {
  assert.equal(typeof routing.remainingPolylinePoints, 'function');
  const points = [[0,0],[100,0],[100,100],[200,100]];
  const progress = routing.nearestPolylineProgress([30,8], points);
  const remaining = routing.remainingPolylinePoints(points, progress);
  assert.deepEqual(remaining, [[30,0],[100,0],[100,100],[200,100]]);
});

test('remainingPolylinePoints avoids a duplicate vertex when progress is exactly at a segment end', () => {
  assert.equal(typeof routing.remainingPolylinePoints, 'function');
  const points = [[0,0],[100,0],[100,100]];
  const progress = {segmentIndex:0, t:1, point:[100,0], distancePx:0};
  assert.deepEqual(routing.remainingPolylinePoints(points, progress), [[100,0],[100,100]]);
});

test('waypoint optimizer visits a future POI when the road to an earlier target already passes through it', () => {
  assert.equal(typeof routing.optimizeWaypointOrderByFirstVisit, 'function');
  const roads = [
    {type:'asphalt', points:[{x:0,y:0},{x:10,y:0},{x:20,y:0}]},
    {type:'asphalt', points:[{x:20,y:0},{x:20,y:10},{x:0,y:10},{x:0,y:0}]},
  ];
  const graph = routing.buildRoadGraph(roads);
  const a = routing.labToMapPixel(0,0);
  const b = routing.labToMapPixel(20,0);
  const c = routing.labToMapPixel(10,0);
  const optimized = routing.optimizeWaypointOrderByFirstVisit([a,b,c], graph, {
    loop:true,
    avoidDirt:true,
    reusePenalty:6,
    maxIterations:4,
  });
  assert.deepEqual(optimized.order, [0,2,1]);
});

test('waypoint optimizer keeps the starting waypoint anchored and preserves every waypoint exactly once', () => {
  const roads = [
    {type:'asphalt', points:[{x:0,y:0},{x:10,y:0},{x:20,y:0},{x:30,y:0}]},
    {type:'asphalt', points:[{x:30,y:0},{x:30,y:20},{x:0,y:20},{x:0,y:0}]},
  ];
  const graph = routing.buildRoadGraph(roads);
  const points = [0,30,10,20].map(x => routing.labToMapPixel(x,0));
  const optimized = routing.optimizeWaypointOrderByFirstVisit(points, graph, {loop:true, avoidDirt:true, maxIterations:5});
  assert.equal(optimized.order[0], 0);
  assert.deepEqual([...optimized.order].sort((a,b)=>a-b), [0,1,2,3]);
});
