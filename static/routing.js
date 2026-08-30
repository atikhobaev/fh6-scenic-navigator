// Road routing over the FH6 road graph published by ForzaLabs.
// Map calibration constants are independently implemented from the MIT-licensed
// ForzaDrive reference (Gerard Alvear, 2026). See THIRD_PARTY_NOTICES.md.

const MAPGENIE_PIXEL_MIN = 2080768;
const LAB_TO_Z12_A = 0.70688367;
const LAB_TO_Z12_B = 0.00036652;
const LAB_TO_Z12_C = 1370.9325;
const LAB_TO_Z12_D = 0.00004749;
const LAB_TO_Z12_E = 0.70754216;
const LAB_TO_Z12_F = 1089.5011;

export function labToMapPixel(x, y) {
  const z12X = LAB_TO_Z12_A * x + LAB_TO_Z12_B * y + LAB_TO_Z12_C;
  const z12Y = LAB_TO_Z12_D * x + LAB_TO_Z12_E * y + LAB_TO_Z12_F;
  return [MAPGENIE_PIXEL_MIN + z12X * 4, MAPGENIE_PIXEL_MIN + z12Y * 4];
}

function isDirt(type) {
  return type === 'dirt' || type === 'dirtSnow';
}

function edgeKey(a, b) {
  return a < b ? `${a}:${b}` : `${b}:${a}`;
}

function asphaltDegree(nodeId, graph) {
  const unique = new Set();
  for (const edge of graph.adjacency[nodeId] || []) {
    if (!isDirt(edge.type)) unique.add(edge.to);
  }
  return unique.size;
}

function fallbackRoadWeight(type) {
  if (type === 'dirtSnow') return 80;
  if (type === 'dirt') return 60;
  return 1;
}

export function buildRoadGraph(roads) {
  const nodes = [];
  const adjacency = [];
  const nodeByKey = new Map();
  const edgePairs = [];

  function nodeFor(point) {
    const x = Number(point.x);
    const y = Number(point.y);
    const key = `${Math.trunc(x)}_${Math.trunc(y)}`;
    let id = nodeByKey.get(key);
    if (id === undefined) {
      id = nodes.length;
      nodes.push({id, x, y, pixel: labToMapPixel(x, y)});
      adjacency.push([]);
      nodeByKey.set(key, id);
    }
    return id;
  }

  for (const road of Array.isArray(roads) ? roads : []) {
    const pts = Array.isArray(road.points) ? road.points : [];
    const type = road.type || 'asphalt';
    let previous = null;
    for (const point of pts) {
      const current = nodeFor(point);
      if (previous !== null && previous !== current) {
        const a = nodes[previous], b = nodes[current];
        const distance = Math.hypot(b.x - a.x, b.y - a.y);
        adjacency[previous].push({to: current, distance, type});
        adjacency[current].push({to: previous, distance, type});
        edgePairs.push([previous, current, type]);
      }
      previous = current;
    }
  }
  return {nodes, adjacency, edges: edgePairs};
}

export function nearestRoadNode(pixel, graph) {
  let bestId = -1;
  let bestDistance = Infinity;
  for (const node of graph.nodes) {
    const d = Math.hypot(pixel[0] - node.pixel[0], pixel[1] - node.pixel[1]);
    if (d < bestDistance) {
      bestDistance = d;
      bestId = node.id;
    }
  }
  return {id: bestId, distancePx: bestDistance};
}

export function nearestSuitableRoadNode(pixel, graph, {surface='any', minDegree=0} = {}) {
  let bestId = -1;
  let bestDistance = Infinity;
  for (const node of graph.nodes) {
    if (surface === 'asphalt' && asphaltDegree(node.id, graph) < Math.max(1, minDegree)) continue;
    if (surface !== 'asphalt' && minDegree > 0) {
      const degree = new Set((graph.adjacency[node.id] || []).map(edge => edge.to)).size;
      if (degree < minDegree) continue;
    }
    const d = Math.hypot(pixel[0] - node.pixel[0], pixel[1] - node.pixel[1]);
    if (d < bestDistance) {
      bestDistance = d;
      bestId = node.id;
    }
  }
  if (bestId < 0) return nearestRoadNode(pixel, graph);
  return {id: bestId, distancePx: bestDistance};
}

class MinHeap {
  constructor() { this.a = []; }
  push(item) {
    const a = this.a;
    a.push(item);
    let i = a.length - 1;
    while (i > 0) {
      const p = (i - 1) >> 1;
      if (a[p][0] <= item[0]) break;
      a[i] = a[p]; i = p;
    }
    a[i] = item;
  }
  pop() {
    const a = this.a;
    if (!a.length) return null;
    const root = a[0];
    const last = a.pop();
    if (a.length && last) {
      let i = 0;
      while (true) {
        const l = i * 2 + 1, r = l + 1;
        if (l >= a.length) break;
        let c = l;
        if (r < a.length && a[r][0] < a[l][0]) c = r;
        if (a[c][0] >= last[0]) break;
        a[i] = a[c]; i = c;
      }
      a[i] = last;
    }
    return root;
  }
  get size() { return this.a.length; }
}

function dijkstra(startId, endId, graph, {
  asphaltOnly=false,
  weightedDirt=false,
  usedEdges=null,
  reusePenalty=0,
  bannedEdges=null,
} = {}) {
  if (startId < 0 || endId < 0) return [];
  if (startId === endId) return [startId];
  const n = graph.nodes.length;
  const dist = new Float64Array(n);
  dist.fill(Infinity);
  const prev = new Int32Array(n);
  prev.fill(-1);
  const heap = new MinHeap();
  dist[startId] = 0;
  heap.push([0, startId]);

  while (heap.size) {
    const item = heap.pop();
    if (!item) break;
    const [currentDist, id] = item;
    if (currentDist !== dist[id]) continue;
    if (id === endId) break;
    for (const edge of graph.adjacency[id] || []) {
      if (asphaltOnly && isDirt(edge.type)) continue;
      const key = edgeKey(id, edge.to);
      if (bannedEdges?.has(key)) continue;
      const surfaceWeight = weightedDirt ? fallbackRoadWeight(edge.type) : 1;
      const reuseCount = usedEdges?.get(key) || 0;
      const reuseWeight = 1 + Math.max(0, reusePenalty) * reuseCount;
      const next = currentDist + edge.distance * surfaceWeight * reuseWeight;
      if (next < dist[edge.to]) {
        dist[edge.to] = next;
        prev[edge.to] = id;
        heap.push([next, edge.to]);
      }
    }
  }
  if (!Number.isFinite(dist[endId])) return [];
  const path = [];
  for (let id = endId; id !== -1; id = prev[id]) path.push(id);
  path.reverse();
  return path;
}

export function shortestPath(startId, endId, graph, {
  avoidDirt=false,
  usedEdges=null,
  reusePenalty=0,
  bannedEdges=null,
} = {}) {
  const common = {usedEdges, reusePenalty, bannedEdges};
  if (!avoidDirt) return dijkstra(startId, endId, graph, common);
  const asphaltPath = dijkstra(startId, endId, graph, {...common, asphaltOnly:true});
  if (asphaltPath.length) return asphaltPath;
  return dijkstra(startId, endId, graph, {...common, weightedDirt:true});
}

export function routeThroughWaypoints(waypointPixels, graph, {
  loop=false,
  avoidDirt=true,
  reusePenalty=0,
  avoidImmediateBacktrack=false,
  waypointNodeIds=null,
} = {}) {
  if (!Array.isArray(waypointPixels) || waypointPixels.length === 0 || !graph.nodes.length) {
    return {points: [], legs: [], waypointNodeIds: []};
  }
  const snappedIds = Array.isArray(waypointNodeIds) && waypointNodeIds.length === waypointPixels.length
    ? [...waypointNodeIds]
    : waypointPixels.map(p => nearestRoadNode(p, graph).id);
  const pairCount = loop && snappedIds.length > 1 ? snappedIds.length : Math.max(0, snappedIds.length - 1);
  const legs = [];
  const points = [];
  const usedEdges = new Map();
  let previousLastEdge = null;

  for (let i = 0; i < pairCount; i++) {
    const from = snappedIds[i];
    const to = snappedIds[(i + 1) % snappedIds.length];
    let bannedEdges = null;
    if (avoidImmediateBacktrack && previousLastEdge) {
      bannedEdges = new Set([edgeKey(previousLastEdge[0], previousLastEdge[1])]);
    }
    let nodeIds = shortestPath(from, to, graph, {avoidDirt, usedEdges, reusePenalty, bannedEdges});
    if (!nodeIds.length && bannedEdges) {
      nodeIds = shortestPath(from, to, graph, {avoidDirt, usedEdges, reusePenalty});
    }
    if (!nodeIds.length) {
      legs.push({fromIndex:i, toIndex:(i+1)%snappedIds.length, nodeIds:[], points:[]});
      previousLastEdge = null;
      continue;
    }
    for (let j=0; j<nodeIds.length-1; j++) {
      const key = edgeKey(nodeIds[j], nodeIds[j+1]);
      usedEdges.set(key, (usedEdges.get(key) || 0) + 1);
    }
    previousLastEdge = nodeIds.length >= 2 ? [nodeIds.at(-2), nodeIds.at(-1)] : null;
    const legPoints = nodeIds.map(id => graph.nodes[id].pixel);
    legs.push({fromIndex:i, toIndex:(i+1)%snappedIds.length, nodeIds, points:legPoints});
    if (!points.length) points.push(...legPoints);
    else points.push(...legPoints.slice(1));
  }
  return {points, legs, waypointNodeIds: snappedIds, usedEdges};
}

export function nearestPolylineProgress(pixel, points) {
  if (!Array.isArray(points) || points.length === 0) {
    return {segmentIndex:-1, t:0, point:[pixel[0], pixel[1]], distancePx:Infinity};
  }
  if (points.length === 1) {
    return {segmentIndex:0, t:0, point:[...points[0]], distancePx:Math.hypot(pixel[0]-points[0][0], pixel[1]-points[0][1])};
  }
  let best = {segmentIndex:0, t:0, point:[...points[0]], distancePx:Infinity};
  for (let i=0; i<points.length-1; i++) {
    const a=points[i], b=points[i+1];
    const dx=b[0]-a[0], dy=b[1]-a[1];
    const lenSq=dx*dx+dy*dy;
    const t=lenSq <= 1e-12 ? 0 : Math.max(0,Math.min(1,((pixel[0]-a[0])*dx+(pixel[1]-a[1])*dy)/lenSq));
    const q=[a[0]+dx*t,a[1]+dy*t];
    const d=Math.hypot(pixel[0]-q[0],pixel[1]-q[1]);
    if (d < best.distancePx) best={segmentIndex:i,t,point:q,distancePx:d};
  }
  return best;
}

export function pointAheadOnPolyline(points, progress, advancePx) {
  if (!Array.isArray(points) || points.length === 0) return [0,0];
  if (points.length === 1 || progress.segmentIndex < 0) return [...points.at(-1)];
  let remaining=Math.max(0,advancePx);
  let current=[...progress.point];
  let i=Math.min(progress.segmentIndex,points.length-2);
  while (i < points.length-1) {
    const end=points[i+1];
    const seg=Math.hypot(end[0]-current[0],end[1]-current[1]);
    if (seg >= remaining && seg > 1e-12) {
      const t=remaining/seg;
      return [current[0]+(end[0]-current[0])*t,current[1]+(end[1]-current[1])*t];
    }
    remaining-=seg;
    i+=1;
    current=i < points.length ? [...points[i]] : [...end];
  }
  return [...points.at(-1)];
}

export function remainingPolylineDistancePx(points, progress) {
  if (!Array.isArray(points) || points.length < 2 || progress.segmentIndex < 0) return 0;
  let total=0;
  let current=progress.point;
  for (let i=progress.segmentIndex; i<points.length-1; i++) {
    const end=points[i+1];
    total += Math.hypot(end[0]-current[0],end[1]-current[1]);
    current=end;
  }
  return total;
}

export function remainingPolylinePoints(points, progress) {
  if (!Array.isArray(points) || points.length < 2 || !progress || progress.segmentIndex < 0) return [];
  const i = Math.min(progress.segmentIndex, points.length - 2);
  const result = [[progress.point[0], progress.point[1]]];
  for (let j = i + 1; j < points.length; j++) {
    const prev = result.at(-1);
    const next = points[j];
    if (Math.hypot(next[0]-prev[0], next[1]-prev[1]) > 1e-9) result.push([next[0], next[1]]);
  }
  return result;
}

export function distanceAlongPolylinePx(points, progress) {
  if (!Array.isArray(points) || points.length < 2 || progress.segmentIndex < 0) return 0;
  let total = 0;
  const upto = Math.min(progress.segmentIndex, points.length - 2);
  for (let i = 0; i < upto; i++) {
    total += Math.hypot(points[i+1][0]-points[i][0], points[i+1][1]-points[i][1]);
  }
  total += Math.hypot(progress.point[0]-points[upto][0], progress.point[1]-points[upto][1]);
  return total;
}

function signedDeltaDeg(inBearing, outBearing) {
  return ((outBearing - inBearing + 540) % 360) - 180;
}

function bearingDeg(a, b) {
  return Math.atan2(b[0]-a[0], -(b[1]-a[1])) * 180 / Math.PI;
}

function sampleAway(points, index, direction, wantedDistance) {
  let remaining = Math.max(0, wantedDistance);
  let current = points[index];
  let i = index;
  while (true) {
    const nextIndex = i + direction;
    if (nextIndex < 0 || nextIndex >= points.length) return points[i];
    const next = points[nextIndex];
    const seg = Math.hypot(next[0]-current[0], next[1]-current[1]);
    if (seg >= remaining && seg > 1e-9) {
      const t = remaining / seg;
      return [current[0] + (next[0]-current[0])*t, current[1] + (next[1]-current[1])*t];
    }
    remaining -= seg;
    i = nextIndex;
    current = next;
    if (remaining <= 1e-9) return current;
  }
}

function classifyManeuver(deltaDeg) {
  const abs = Math.abs(deltaDeg);
  if (abs < 20) return null;
  const direction = deltaDeg > 0 ? 'right' : 'left';
  let kind = 'keep';
  if (abs >= 45) kind = 'turn';
  if (abs >= 120) kind = 'sharp';
  if (abs >= 165) kind = 'uturn';
  return {direction, kind};
}

export function detectManeuvers(nodeIds, graph, {
  lookDistancePx=20,
  minTurnDeg=20,
  mergeDistancePx=30,
} = {}) {
  if (!Array.isArray(nodeIds) || nodeIds.length < 3) return [];
  const points = nodeIds.map(id => graph.nodes[id].pixel);
  const cumulative = new Float64Array(points.length);
  for (let i=1; i<points.length; i++) {
    cumulative[i] = cumulative[i-1] + Math.hypot(points[i][0]-points[i-1][0], points[i][1]-points[i-1][1]);
  }
  const maneuvers = [];
  for (let i=1; i<nodeIds.length-1; i++) {
    const uniqueNeighbors = new Set((graph.adjacency[nodeIds[i]] || []).map(edge => edge.to));
    if (uniqueNeighbors.size < 3) continue;
    const before = sampleAway(points, i, -1, lookDistancePx);
    const after = sampleAway(points, i, 1, lookDistancePx);
    const incoming = bearingDeg(before, points[i]);
    const outgoing = bearingDeg(points[i], after);
    const deltaDeg = signedDeltaDeg(incoming, outgoing);
    if (Math.abs(deltaDeg) < minTurnDeg) continue;
    const classification = classifyManeuver(deltaDeg);
    if (!classification) continue;
    const maneuver = {
      pathIndex: i,
      nodeId: nodeIds[i],
      point: points[i],
      distanceFromStartPx: cumulative[i],
      deltaDeg,
      ...classification,
    };
    const previous = maneuvers.at(-1);
    if (previous && maneuver.distanceFromStartPx - previous.distanceFromStartPx < mergeDistancePx) {
      if (Math.abs(maneuver.deltaDeg) > Math.abs(previous.deltaDeg)) maneuvers[maneuvers.length-1] = maneuver;
    } else {
      maneuvers.push(maneuver);
    }
  }
  return maneuvers;
}

export function nextManeuver(maneuvers, points, progress, {passedTolerancePx=2} = {}) {
  if (!Array.isArray(maneuvers) || !maneuvers.length) return null;
  const currentDistance = distanceAlongPolylinePx(points, progress);
  for (const maneuver of maneuvers) {
    const distancePx = maneuver.distanceFromStartPx - currentDistance;
    if (distancePx > passedTolerancePx) return {...maneuver, distancePx};
  }
  return null;
}

export function optimizeWaypointOrderByFirstVisit(waypointPixels, graph, {
  loop=true,
  avoidDirt=true,
  reusePenalty=0,
  avoidImmediateBacktrack=true,
  waypointNodeIds=null,
  maxIterations=4,
} = {}) {
  if (!Array.isArray(waypointPixels) || waypointPixels.length <= 2 || !graph?.nodes?.length) {
    const order = Array.isArray(waypointPixels) ? waypointPixels.map((_, i) => i) : [];
    return {order, iterations:0};
  }

  const originalNodeIds = Array.isArray(waypointNodeIds) && waypointNodeIds.length === waypointPixels.length
    ? [...waypointNodeIds]
    : waypointPixels.map(p => nearestRoadNode(p, graph).id);
  let order = waypointPixels.map((_, i) => i);
  let iterations = 0;

  for (; iterations < Math.max(1, maxIterations); iterations++) {
    const orderedPixels = order.map(i => waypointPixels[i]);
    const orderedNodeIds = order.map(i => originalNodeIds[i]);
    const result = routeThroughWaypoints(orderedPixels, graph, {
      loop,
      avoidDirt,
      reusePenalty,
      avoidImmediateBacktrack,
      waypointNodeIds: orderedNodeIds,
    });
    if (result.legs.some(leg => leg.nodeIds.length < 2)) break;

    const firstVisit = new Map();
    let pathPosition = 0;
    for (const leg of result.legs) {
      for (let j = 0; j < leg.nodeIds.length; j++) {
        if (pathPosition > 0 && j === 0) continue;
        const id = leg.nodeIds[j];
        if (!firstVisit.has(id)) firstVisit.set(id, pathPosition);
        pathPosition++;
      }
    }

    const previousRank = new Map(order.map((originalIndex, rank) => [originalIndex, rank]));
    const nextInterior = order.slice(1).sort((a, b) => {
      const pa = firstVisit.get(originalNodeIds[a]);
      const pb = firstVisit.get(originalNodeIds[b]);
      const va = Number.isFinite(pa) ? pa : Infinity;
      const vb = Number.isFinite(pb) ? pb : Infinity;
      return va - vb || previousRank.get(a) - previousRank.get(b);
    });
    const nextOrder = [order[0], ...nextInterior];
    if (nextOrder.every((value, i) => value === order[i])) break;
    order = nextOrder;
  }

  return {order, iterations};
}
