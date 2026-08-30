export const TILE_ZOOM = 14;
export const CAL_A_WORLD = [-119.49154, 3888.595];
export const CAL_A_PIX = [2089486, 2087415];
export const CAL_B_WORLD = [-7104.7695, -1863.08];
export const CAL_B_PIX = [2086885, 2089556];

const MX = (CAL_B_PIX[0] - CAL_A_PIX[0]) / (CAL_B_WORLD[0] - CAL_A_WORLD[0]);
const MZ = (CAL_B_PIX[1] - CAL_A_PIX[1]) / (CAL_B_WORLD[1] - CAL_A_WORLD[1]);
const BX = CAL_A_PIX[0] - MX * CAL_A_WORLD[0];
const BY = CAL_A_PIX[1] - MZ * CAL_A_WORLD[1];
export const PX_PER_WORLD_M = (Math.abs(MX) + Math.abs(MZ)) / 2;

export function worldToPixel(worldX, worldZ) {
  return [MX * worldX + BX, MZ * worldZ + BY];
}
export function pixelToWorld(pixelX, pixelY) {
  return [(pixelX - BX) / MX, (pixelY - BY) / MZ];
}
export function hubToPixel(lat, lng) {
  const worldSize = 256 * (2 ** TILE_ZOOM);
  const latRad = lat * Math.PI / 180;
  const x = (lng + 180) / 360 * worldSize;
  const y = (1 - Math.asinh(Math.tan(latRad)) / Math.PI) / 2 * worldSize;
  return [x, y];
}
export function pixelsToWorldMeters(px) {
  return px / PX_PER_WORLD_M;
}
export function distanceToSegmentPx(p, a, b) {
  const [px, py] = p, [ax, ay] = a, [bx, by] = b;
  const abx = bx - ax, aby = by - ay;
  const denom = abx * abx + aby * aby;
  if (!denom) return Math.hypot(px - ax, py - ay);
  const t = Math.max(0, Math.min(1, ((px - ax) * abx + (py - ay) * aby) / denom));
  const qx = ax + t * abx, qy = ay + t * aby;
  return Math.hypot(px - qx, py - qy);
}
export function nearestPolylineDistancePx(p, points) {
  if (!points || points.length === 0) return Infinity;
  if (points.length === 1) return Math.hypot(p[0] - points[0][0], p[1] - points[0][1]);
  let best = Infinity;
  for (let i = 0; i < points.length - 1; i++) {
    best = Math.min(best, distanceToSegmentPx(p, points[i], points[i + 1]));
  }
  return best;
}
export function formatGear(gear) {
  if (gear === 0) return 'R';
  if (gear === 11) return 'N';
  return String(gear ?? '—');
}
export function bearingDeg(fromPx, toPx) {
  const dx = toPx[0] - fromPx[0];
  const dy = toPx[1] - fromPx[1];
  return Math.atan2(dx, -dy) * 180 / Math.PI;
}
export function normalizeDeg(deg) {
  return ((deg % 360) + 360) % 360;
}
export function nearestWaypointIndex(p, points) {
  if (!points || points.length === 0) return -1;
  let bestIndex = 0;
  let best = Infinity;
  for (let i = 0; i < points.length; i++) {
    const d = Math.hypot(p[0] - points[i][0], p[1] - points[i][1]);
    if (d < best) { best = d; bestIndex = i; }
  }
  return bestIndex;
}
export function maybeAdvanceWaypoint(p, points, activeIndex, reachRadiusPx) {
  if (!points || activeIndex < 0 || activeIndex >= points.length) return activeIndex;
  const target = points[activeIndex];
  const d = Math.hypot(p[0] - target[0], p[1] - target[1]);
  if (d <= reachRadiusPx && activeIndex < points.length - 1) return activeIndex + 1;
  return activeIndex;
}

export function maybeAdvanceLoopWaypoint(p, points, activeIndex, reachRadiusPx, loop=false) {
  if (!points || activeIndex < 0 || activeIndex >= points.length) return activeIndex;
  const target = points[activeIndex];
  const d = Math.hypot(p[0] - target[0], p[1] - target[1]);
  if (d > reachRadiusPx) return activeIndex;
  if (activeIndex < points.length - 1) return activeIndex + 1;
  if (loop && points.length > 1) return 1;
  return activeIndex;
}

export function withLoopClosure(waypoints) {
  if (!Array.isArray(waypoints) || waypoints.length === 0) return [];
  const result = waypoints.map(w => ({...w}));
  const first = waypoints[0];
  result.push({
    ...first,
    name: `Возвращение: ${first.name}`,
    loopClosure: true,
  });
  return result;
}

export function buildDirectionalLoop(waypoints, direction='forward') {
  if (!Array.isArray(waypoints) || waypoints.length === 0) return [];
  const first = {...waypoints[0]};
  const interior = waypoints.slice(1).map(w => ({...w}));
  if (direction === 'reverse') interior.reverse();
  const result = [first, ...interior];
  result.push({
    ...first,
    name: `Возвращение: ${first.name}`,
    loopClosure: true,
  });
  return result;
}


export function tileValidRange(z, mapMaxZoom=TILE_ZOOM) {
  const div = 2 ** (mapMaxZoom - z);
  return [Math.floor(8128 / div), Math.ceil(8192 / div) - 1];
}

export function tileDisplayPlan(viewZoom, mapMaxZoom=TILE_ZOOM, minSourceZoom=11) {
  const sourceZoom = Math.min(mapMaxZoom, Math.max(minSourceZoom, viewZoom));
  const displayScale = 2 ** (viewZoom - sourceZoom);
  return {sourceZoom, displayScale};
}

export function nextAutoZoomState({
  speedKmh,
  follow,
  zoom,
  active=false,
  savedZoom=null,
  maxZoom=15,
  engageBelow=40,
  releaseAbove=45,
}) {
  if (!follow) return {zoom, active:false, savedZoom:null};
  const speed = Number(speedKmh);
  if (!Number.isFinite(speed)) return {zoom, active, savedZoom};

  if (!active && speed < engageBelow) {
    return {zoom:maxZoom, active:true, savedZoom:zoom};
  }
  if (active && speed > releaseAbove) {
    return {zoom:Number.isFinite(savedZoom) ? savedZoom : zoom, active:false, savedZoom:null};
  }
  if (active) return {zoom:maxZoom, active:true, savedZoom};
  return {zoom, active:false, savedZoom:null};
}
export function turnAlertLevel(distanceMeters) {
  const meters = Number(distanceMeters);
  if (!Number.isFinite(meters) || meters > 500) return 'none';
  if (meters <= 100) return 'urgent';
  if (meters <= 300) return 'near';
  return 'far';
}

