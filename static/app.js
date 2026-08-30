import {
  TILE_ZOOM, PX_PER_WORLD_M, worldToPixel, pixelToWorld, hubToPixel,
  pixelsToWorldMeters, nearestPolylineDistancePx, formatGear, bearingDeg,
  normalizeDeg, nearestWaypointIndex, maybeAdvanceWaypoint, maybeAdvanceLoopWaypoint, buildDirectionalLoop,
  tileDisplayPlan, tileValidRange, nextAutoZoomState, turnAlertLevel
} from './nav_logic.js';
import {
  buildRoadGraph, nearestPolylineProgress,
  pointAheadOnPolyline, remainingPolylineDistancePx, remainingPolylinePoints,
  nextManeuver, nearestRoadNode, nearestSuitableRoadNode, optimizeWaypointOrderByFirstVisit
} from './routing.js';
import {
  buildDirectedRuntime, matchDirectedSegment, routeFromMatch, routeBetweenWorldPoints,
  nextRerouteState, routeManeuvers
} from './directed_nav.js';
import {plannerGuidanceFromMatch,plannerProgressModel,shouldCompletePlannerItem} from './planner_drive.js';
import {applyTranslations,bindLocaleFlagMenu,getLocale,t} from './i18n.js';
import {loadPlaceNames,localizedGameName,localizedRouteItemName} from './place_locale.js';
import {installTooltips} from './tooltips.js';

const MAP_MAX_ZOOM = TILE_ZOOM;
const VIEW_MAX_ZOOM = 15;
const MAP_MIN_ZOOM = 9;
const MAP_MIN_MAXPX = 8128 * 256;
const MAP_MAX_MAXPX = 8192 * 256;
const REACH_METERS = 350;
const OFF_ROUTE_METERS = 45;
const REROUTE_CONFIRM_MS = 800;
const REROUTE_MIN_CONFIDENCE = 0.45;
const RECORD_SPACING_METERS = 12;
const STORAGE_PROGRESS = 'fh6-scenic-progress-v4';
const STORAGE_TARGET = 'fh6-scenic-target-v1';
const STORAGE_DIRECTION = 'fh6-scenic-direction-v1';
const STORAGE_TRACK = 'fh6-scenic-recorded-track-v1';
const STORAGE_ROADS_VISIBLE = 'fh6-scenic-roads-visible-v1';
const STORAGE_AUTO_ZOOM = 'fh6-scenic-auto-zoom-v1';
const ROAD_BUCKET_PX = 640;

const mapEl = document.getElementById('map');
const tilesEl = document.getElementById('tiles');
const roadsCanvas = document.getElementById('roadsCanvas');
const roadsCtx = roadsCanvas.getContext('2d');
const svg = document.getElementById('overlay');
const connDot = document.getElementById('connDot');
const connText = document.getElementById('connText');
const speedEl = document.getElementById('speed');
const gearEl = document.getElementById('gear');
const rpmText = document.getElementById('rpmText');
const rpmBar = document.getElementById('rpmBar');
const nextTitle = document.getElementById('nextTitle');
const nextGame = document.getElementById('nextGame');
const distanceEl = document.getElementById('distance');
const progressEl = document.getElementById('progress');
const navArrowSvg = document.getElementById('navArrowSvg');
const offRouteEl = document.getElementById('offRoute');
const toastEl = document.getElementById('toast');
const panel = document.getElementById('panel');
const waypointList = document.getElementById('waypointList');
const roadsBtn = document.getElementById('roadsBtn');
const autoZoomBtn = document.getElementById('autoZoomBtn');
const turnCard = document.getElementById('turnCard');
const turnIcon = document.getElementById('turnIcon');
const turnInstruction = document.getElementById('turnInstruction');
const turnDistance = document.getElementById('turnDistance');
const directionBtn = document.getElementById('directionBtn');
const routingStatusEl = document.getElementById('routingStatus');
const plannerSkipStop = document.getElementById('plannerSkipStop');
const plannerPreviousStop = document.getElementById('plannerPreviousStop');
const plannerSessionControls = document.getElementById('plannerSessionControls');

let route = null;
let navigationWaypoints = [];
let rawWaypointPixels = [];
let waypointPixels = [];
let waypointNodeIds = [];
let roadRoute = null;
let roadRoutePixels = [];
let roadGraph = null;
let directedRuntime = null;
let currentDirectedMatch = null;
let previousDirectedSegmentId = null;
let rerouteState = {pendingSince:null, shouldReroute:false};
let routingFailClosed = false;
let roadBuckets = new Map();
let roadLayerVisible = localStorage.getItem(STORAGE_ROADS_VISIBLE) !== '0';
let currentManeuver = null;
let manualLeg = null;
let guidancePolyline = [];
let direction = localStorage.getItem(STORAGE_DIRECTION) === 'reverse' ? 'reverse' : 'forward';
let roadRoutingError = '';
let waypointOrderOptimized = false;
let optimizedMoveCount = 0;
let center = [2088960, 2088960];
let zoom = 11;
let follow = true;
let autoZoomEnabled = localStorage.getItem(STORAGE_AUTO_ZOOM) !== '0';
let autoZoomActive = false;
let autoZoomRestoreZoom = null;
let car = null;
let activeIndex = Number(localStorage.getItem(STORAGE_PROGRESS));
if (!Number.isFinite(activeIndex)) activeIndex = -1;
let recordedTrack = loadRecordedTrack();
let recording = false;
let recordBuffer = [];
let firstTelemetry = true;
let tileNodes = new Map();
let toastTimer = null;
let pollBusy = false;
let drag = null;
let plannerNavigation = null;
let plannerLeg = null;
let plannerRoutePixels = [];
let plannerRouteMarkers = [];
let plannerEvents = null;
let plannerCompletionBusy = false;
let plannerCompletionItemId = null;
let drivePlacesById = new Map();

function loadRecordedTrack() {
  try {
    const raw = JSON.parse(localStorage.getItem(STORAGE_TRACK) || '[]');
    if (!Array.isArray(raw)) return [];
    return raw.filter(p => Array.isArray(p) && p.length === 2 && Number.isFinite(p[0]) && Number.isFinite(p[1]));
  } catch { return []; }
}

function saveRecordedTrack(points) {
  recordedTrack = points;
  localStorage.setItem(STORAGE_TRACK, JSON.stringify(points));
}

function autoZoomTooltipText() {
  return autoZoomEnabled ? t('drive.autoZoomOn') : t('drive.autoZoomOff');
}
function waypointDisplayName(waypoint){
  return localizedGameName(waypoint?.game||waypoint?.name||'',getLocale()) || String(waypoint?.game||waypoint?.name||'');
}
function refreshCurrentTargetCopy(){
  if(plannerSessionActive()){
    const items=plannerNavigation.route?.items||[],currentId=plannerNavigation.session.current_item_id;
    const idx=Math.max(0,items.findIndex(x=>x.id===currentId));
    nextTitle.textContent=plannerItemLabel(items[idx]);
    nextGame.textContent=`${t('drive.plannerRoute')} · ${plannerNavigation.route?.name||t('common.route')}`;
    return;
  }
  const waypoint=navigationWaypoints[activeIndex];
  if(waypoint){nextTitle.textContent=waypointDisplayName(waypoint);nextGame.textContent=t('common.officialGame')}
}

function refreshAutoZoomButton() {
  if (!autoZoomBtn) return;
  autoZoomBtn.classList.toggle('active', autoZoomEnabled);
  autoZoomBtn.setAttribute('aria-pressed', autoZoomEnabled ? 'true' : 'false');
  autoZoomBtn.removeAttribute('title');
  autoZoomBtn.setAttribute('aria-label', autoZoomTooltipText());
  autoZoomBtn.innerHTML = `${autoZoomEnabled ? '☑' : '☐'} <span class="wide">${t('drive.autoZoom')}</span>`;
}

function showToast(text, ms=2600) {
  toastEl.textContent = text;
  toastEl.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toastEl.classList.remove('show'), ms);
}

function clampCenter() {
  center[0] = Math.max(MAP_MIN_MAXPX, Math.min(MAP_MAX_MAXPX, center[0]));
  center[1] = Math.max(MAP_MIN_MAXPX, Math.min(MAP_MAX_MAXPX, center[1]));
}

function scaleForZoom() { return 2 ** (MAP_MAX_ZOOM - zoom); }
function toScreen(p) {
  const s = scaleForZoom();
  return [(p[0] - center[0]) / s + mapEl.clientWidth/2, (p[1] - center[1]) / s + mapEl.clientHeight/2];
}
function fromScreen(x,y) {
  const s = scaleForZoom();
  return [(x - mapEl.clientWidth/2)*s + center[0], (y - mapEl.clientHeight/2)*s + center[1]];
}

function updateTiles() {
  const {sourceZoom, displayScale} = tileDisplayPlan(zoom, MAP_MAX_ZOOM);
  const sourceDiv = 2 ** (MAP_MAX_ZOOM - sourceZoom);
  const cx = center[0] / sourceDiv, cy = center[1] / sourceDiv;
  const w = mapEl.clientWidth, h = mapEl.clientHeight;
  const halfW = w / (2 * displayScale), halfH = h / (2 * displayScale);
  const x0 = Math.floor((cx - halfW)/256)-1;
  const x1 = Math.floor((cx + halfW)/256)+1;
  const y0 = Math.floor((cy - halfH)/256)-1;
  const y1 = Math.floor((cy + halfH)/256)+1;
  const [lo, hi] = tileValidRange(sourceZoom, MAP_MAX_ZOOM);
  const needed = new Set();
  for (let ty=y0; ty<=y1; ty++) {
    for (let tx=x0; tx<=x1; tx++) {
      if (tx<lo || tx>hi || ty<lo || ty>hi) continue;
      const key = `${sourceZoom}/${tx}/${ty}`;
      needed.add(key);
      let img = tileNodes.get(key);
      if (!img) {
        img = new Image();
        img.className = 'tile';
        img.alt = '';
        img.decoding = 'async';
        img.draggable = false;
        img.src = `/maptile/${sourceZoom}/${tx}/${ty}.jpg`;
        img.addEventListener('error', () => { img.style.visibility='hidden'; });
        tilesEl.appendChild(img);
        tileNodes.set(key,img);
      }
      const tileSize = 256 * displayScale;
      img.style.width = `${tileSize}px`;
      img.style.height = `${tileSize}px`;
      img.style.left = `${(tx*256 - cx)*displayScale + w/2}px`;
      img.style.top = `${(ty*256 - cy)*displayScale + h/2}px`;
    }
  }
  for (const [key,img] of tileNodes) {
    if (!needed.has(key)) { img.remove(); tileNodes.delete(key); }
  }
}

function buildRoadBuckets(graph) {
  const buckets = new Map();
  for (const [aId, bId, type] of graph.edges || []) {
    const a = graph.nodes[aId]?.pixel;
    const b = graph.nodes[bId]?.pixel;
    if (!a || !b) continue;
    const mx = (a[0] + b[0]) / 2;
    const my = (a[1] + b[1]) / 2;
    const key = `${Math.floor(mx / ROAD_BUCKET_PX)},${Math.floor(my / ROAD_BUCKET_PX)}`;
    const list = buckets.get(key) || [];
    list.push({a, b, type});
    buckets.set(key, list);
  }
  return buckets;
}

function visibleRoadSegments() {
  if (!roadGraph || !roadLayerVisible || !roadBuckets.size) return [];
  const s = scaleForZoom();
  const halfW = mapEl.clientWidth * s / 2;
  const halfH = mapEl.clientHeight * s / 2;
  const pad = ROAD_BUCKET_PX;
  const minBx = Math.floor((center[0] - halfW - pad) / ROAD_BUCKET_PX);
  const maxBx = Math.floor((center[0] + halfW + pad) / ROAD_BUCKET_PX);
  const minBy = Math.floor((center[1] - halfH - pad) / ROAD_BUCKET_PX);
  const maxBy = Math.floor((center[1] + halfH + pad) / ROAD_BUCKET_PX);
  const result = [];
  for (let by = minBy; by <= maxBy; by++) {
    for (let bx = minBx; bx <= maxBx; bx++) {
      const list = roadBuckets.get(`${bx},${by}`);
      if (list) result.push(...list);
    }
  }
  return result;
}

function renderRoadLayer() {
  const dpr = Math.max(1, Math.min(2, window.devicePixelRatio || 1));
  const width = Math.max(1, mapEl.clientWidth);
  const height = Math.max(1, mapEl.clientHeight);
  const targetW = Math.round(width * dpr);
  const targetH = Math.round(height * dpr);
  if (roadsCanvas.width !== targetW || roadsCanvas.height !== targetH) {
    roadsCanvas.width = targetW;
    roadsCanvas.height = targetH;
  }
  roadsCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
  roadsCtx.clearRect(0, 0, width, height);
  if (!roadLayerVisible || !roadGraph) return;

  const segments = visibleRoadSegments();
  const asphalt = [];
  const dirt = [];
  for (const seg of segments) {
    const a = toScreen(seg.a), b = toScreen(seg.b);
    if ((a[0] < -8 && b[0] < -8) || (a[1] < -8 && b[1] < -8) ||
        (a[0] > width + 8 && b[0] > width + 8) || (a[1] > height + 8 && b[1] > height + 8)) continue;
    (seg.type === 'dirt' || seg.type === 'dirtSnow' ? dirt : asphalt).push([a,b]);
  }

  function strokeSegments(list, strokeStyle, lineWidth) {
    if (!list.length) return;
    roadsCtx.beginPath();
    for (const [a,b] of list) {
      roadsCtx.moveTo(a[0], a[1]);
      roadsCtx.lineTo(b[0], b[1]);
    }
    roadsCtx.strokeStyle = strokeStyle;
    roadsCtx.lineWidth = lineWidth;
    roadsCtx.lineCap = 'round';
    roadsCtx.lineJoin = 'round';
    roadsCtx.stroke();
  }

  // Thin dark casing keeps the custom road layer readable over snow and city tiles.
  strokeSegments(asphalt, 'rgba(5,10,15,.70)', 4.0);
  strokeSegments(dirt, 'rgba(5,10,15,.76)', 4.3);
  strokeSegments(asphalt, 'rgba(255,255,255,.92)', 2.1);
  strokeSegments(dirt, 'rgba(255,72,82,.96)', 2.5);
}

function maneuverText(m) {
  if (!m) return '';
  const right = m.direction === 'right';
  if (m.kind === 'keep') return t(right?'drive.keepRight':'drive.keepLeft');
  if (m.kind === 'sharp') return t(right?'drive.sharpRight':'drive.sharpLeft');
  if (m.kind === 'uturn') return t(right?'drive.uturnRight':'drive.uturnLeft');
  return t(right?'drive.turnRight':'drive.turnLeft');
}

function maneuverIcon(m) {
  if (!m) return '';
  const right = m.direction === 'right';
  if (m.kind === 'keep') return right ? '↗' : '↖';
  if (m.kind === 'uturn') return right ? '↷' : '↶';
  if (m.kind === 'sharp') return right ? '↪' : '↩';
  return right ? '↱' : '↰';
}

function setTurnUI(m) {
  currentManeuver = m;
  turnCard.classList.remove('alert-far', 'alert-near', 'alert-urgent');
  if (!m) {
    turnCard.classList.remove('show');
    return;
  }
  const meters = Math.max(0, pixelsToWorldMeters(m.distancePx));
  turnIcon.textContent = maneuverIcon(m);
  turnInstruction.textContent = maneuverText(m);
  if (meters < 35) turnDistance.textContent=t('drive.now');
  else if (meters < 1000) turnDistance.textContent=t('drive.inMeters',{distance:Math.round(meters/10)*10});
  else turnDistance.textContent=t('drive.inKm',{distance:(meters/1000).toFixed(1)});
  const alertLevel = turnAlertLevel(meters);
  if (alertLevel !== 'none') turnCard.classList.add(`alert-${alertLevel}`);
  turnCard.classList.add('show');
}

function svgEl(name, attrs={}) {
  const e = document.createElementNS('http://www.w3.org/2000/svg',name);
  for (const [k,v] of Object.entries(attrs)) e.setAttribute(k,String(v));
  return e;
}
function pointsAttr(points) { return points.map(p=>{const q=toScreen(p);return `${q[0].toFixed(1)},${q[1].toFixed(1)}`;}).join(' '); }

function renderOverlay() {
  svg.replaceChildren();
  if (!route) return;

  const plannedPixels = plannerNavigation ? plannerRoutePixels : roadRoutePixels;
  if (plannedPixels.length > 1) {
    // Dark casing + bright route makes the line readable over snow, city and forest tiles.
    svg.appendChild(svgEl('polyline', {
      points: pointsAttr(plannedPixels), fill:'none', stroke:'#07111c', 'stroke-width':9,
      'stroke-opacity':.72, 'stroke-linecap':'round', 'stroke-linejoin':'round'
    }));
    svg.appendChild(svgEl('polyline', {
      points: pointsAttr(plannedPixels), fill:'none', stroke:'#42a5ff', 'stroke-width':5,
      'stroke-opacity':.96, 'stroke-linecap':'round', 'stroke-linejoin':'round'
    }));
  } else if (!plannerNavigation) {
    // Grand Tour fallback while its road route is downloading. Planner guidance is fail-closed.
    svg.appendChild(svgEl('polyline', {
      points: pointsAttr(waypointPixels), fill:'none', stroke:'#62b7ff', 'stroke-width':4,
      'stroke-opacity':.72, 'stroke-dasharray':'10 9', 'stroke-linecap':'round', 'stroke-linejoin':'round'
    }));
  }

  if (guidancePolyline.length > 1) {
    svg.appendChild(svgEl('polyline', {
      points: pointsAttr(guidancePolyline), fill:'none', stroke:'#ffd166', 'stroke-width':6,
      'stroke-opacity':.98, 'stroke-dasharray':'14 8', 'stroke-linecap':'round', 'stroke-linejoin':'round'
    }));
  }

  if (recordedTrack.length > 1) {
    svg.appendChild(svgEl('polyline', {
      points: pointsAttr(recordedTrack), fill:'none', stroke:'#ffd166', 'stroke-width':6,
      'stroke-opacity':.96, 'stroke-linecap':'round', 'stroke-linejoin':'round'
    }));
  }
  if (recording && recordBuffer.length > 1) {
    svg.appendChild(svgEl('polyline', {
      points: pointsAttr(recordBuffer), fill:'none', stroke:'#ff6670', 'stroke-width':6,
      'stroke-opacity':.95, 'stroke-linecap':'round', 'stroke-linejoin':'round'
    }));
  }

  if (plannerNavigation) {
    plannerRouteMarkers.forEach((m,i)=>{
      const [x,y]=toScreen(m.pixel);
      if (x < -30 || y < -30 || x > mapEl.clientWidth+30 || y > mapEl.clientHeight+30) return;
      const current=m.id===plannerNavigation.session?.current_item_id;
      const circle=svgEl('circle',{cx:x,cy:y,r:current?12:8,fill:current?'#ffd166':'#122434',stroke:current?'#fff':'#62b7ff','stroke-width':current?3:2});
      svg.appendChild(circle);
      const text=svgEl('text',{x,y:y+3.5,'text-anchor':'middle',fill:current?'#111':'#fff','font-size':current?9:8,'font-weight':900});
      text.textContent=String(i+1); svg.appendChild(text);
    });
  } else {
    waypointPixels.forEach((p,i)=>{
      const w = navigationWaypoints[i];
      if (w?.loopClosure) return;
      const [x,y]=toScreen(p);
      if (x < -30 || y < -30 || x > mapEl.clientWidth+30 || y > mapEl.clientHeight+30) return;
      const current=i===activeIndex || (navigationWaypoints[activeIndex]?.loopClosure && i===0);
      const circle=svgEl('circle',{cx:x,cy:y,r:current?12:8,fill:current?'#ffd166':'#122434',stroke:current?'#fff':'#62b7ff','stroke-width':current?3:2});
      svg.appendChild(circle);
      const text=svgEl('text',{x,y:y+3.5,'text-anchor':'middle',fill:current?'#111':'#fff','font-size':current?9:8,'font-weight':900});
      text.textContent=String(i+1); svg.appendChild(text);
    });
  }

  if (currentManeuver?.point) {
    const [mx,my]=toScreen(currentManeuver.point);
    if (mx>-35 && my>-35 && mx<mapEl.clientWidth+35 && my<mapEl.clientHeight+35) {
      svg.appendChild(svgEl('circle',{cx:mx,cy:my,r:13,fill:'rgba(12,18,24,.90)',stroke:'#ffd166','stroke-width':4}));
      const mark=svgEl('text',{x:mx,y:my+6,'text-anchor':'middle',fill:'#ffd166','font-size':18,'font-weight':900});
      mark.textContent=maneuverIcon(currentManeuver); svg.appendChild(mark);
    }
  }

  if (car) {
    const [x,y]=toScreen(car.pixel);
    const g=svgEl('g',{transform:`translate(${x} ${y}) rotate(${car.headingDeg})`});
    const halo=svgEl('circle',{cx:0,cy:0,r:18,fill:'rgba(0,0,0,.40)',stroke:'rgba(255,255,255,.35)','stroke-width':1});
    const arrow=svgEl('path',{d:'M0 -16 L11 14 L0 9 L-11 14 Z',fill:'#ffffff',stroke:'#07101a','stroke-width':2,'stroke-linejoin':'round'});
    g.append(halo,arrow); svg.appendChild(g);
  }
}

function render() { clampCenter(); updateTiles(); renderRoadLayer(); renderOverlay(); }

function fitRoute() {
  const fitPoints = plannerNavigation ? (plannerRoutePixels.length > 1 ? plannerRoutePixels : plannerRouteMarkers.map(x=>x.pixel)) : (roadRoutePixels.length > 1 ? roadRoutePixels : waypointPixels);
  if (!fitPoints.length) return;
  let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity;
  for (const p of fitPoints) { minX=Math.min(minX,p[0]);minY=Math.min(minY,p[1]);maxX=Math.max(maxX,p[0]);maxY=Math.max(maxY,p[1]); }
  center=[(minX+maxX)/2,(minY+maxY)/2];
  const usableW=Math.max(250,mapEl.clientWidth-60), usableH=Math.max(200,mapEl.clientHeight-150);
  for (let z=VIEW_MAX_ZOOM; z>=MAP_MIN_ZOOM; z--) {
    const s=2**(MAP_MAX_ZOOM-z);
    if ((maxX-minX)/s<=usableW && (maxY-minY)/s<=usableH) { zoom=z; break; }
  }
  follow=false; document.getElementById('followBtn').classList.remove('active'); render();
}

function zoomBy(delta, focalX=mapEl.clientWidth/2, focalY=mapEl.clientHeight/2) {
  const before=fromScreen(focalX,focalY);
  const next=Math.max(MAP_MIN_ZOOM,Math.min(VIEW_MAX_ZOOM,zoom+delta));
  if (next===zoom) return;
  zoom=next;
  const s=scaleForZoom();
  center=[before[0]-(focalX-mapEl.clientWidth/2)*s,before[1]-(focalY-mapEl.clientHeight/2)*s];
  render();
}

function refreshDirectionButton() {
  if (!directionBtn) return;
  directionBtn.textContent=direction==='forward'?t('drive.clockwise'):t('drive.counterClockwise');
  directionBtn.classList.toggle('active', direction === 'reverse');
}

function worldTargetForWaypoint(index) {
  const pixel=waypointPixels[index];
  if (!pixel) return null;
  const [x,z]=pixelToWorld(pixel[0],pixel[1]);
  return {x,z};
}

function directedResultToLeg(result, toIndex) {
  if (!result || !directedRuntime) return null;
  const points=result.worldPoints.map(p=>worldToPixel(p.x,p.z));
  return {
    toIndex,
    segmentIds:result.segmentIds,
    segmentSet:new Set(result.segmentIds),
    points,
    maneuvers:routeManeuvers(result,points,directedRuntime),
    distanceM:result.distanceM,
  };
}

function setRoutingStatus(text, state='ok') {
  if (!routingStatusEl) return;
  routingStatusEl.textContent=text;
  routingStatusEl.dataset.state=state;
}

function showNoLegalRoute() {
  routingFailClosed=true;
  offRouteEl.textContent=t('drive.noLegalRoute');
  offRouteEl.classList.add('show');
}

function buildManualLegToActive({reroute=false} = {}) {
  manualLeg = null;
  if (!directedRuntime || !car || activeIndex < 0 || activeIndex >= waypointPixels.length) return false;
  const match=currentDirectedMatch || matchDirectedSegment(
    {x:car.world[0],z:car.world[1]}, car.headingDeg, directedRuntime, previousDirectedSegmentId
  );
  const target=worldTargetForWaypoint(activeIndex);
  if (!match || !target) { showNoLegalRoute(); return false; }
  if (reroute) {
    offRouteEl.textContent=t('drive.rerouting');
    offRouteEl.classList.add('show');
  }
  const result=routeFromMatch(match,target,directedRuntime,{avoidDirt:true});
  const leg=directedResultToLeg(result,activeIndex);
  if (!leg || leg.points.length < 2) { showNoLegalRoute(); return false; }
  manualLeg=leg;
  routingFailClosed=false;
  rerouteState={pendingSince:null,shouldReroute:false};
  offRouteEl.classList.remove('show');
  return true;
}

function refreshWaypointList() {
  if (!route) return;
  waypointList.replaceChildren();
  navigationWaypoints.forEach((w,i)=>{
    if (w.loopClosure) return;
    const li=document.createElement('li');
    if (i===activeIndex || (navigationWaypoints[activeIndex]?.loopClosure && i===0)) li.classList.add('current');
    const button=document.createElement('button');
    button.type='button';
    button.className='waypoint-select';
    button.textContent=`${i+1}. ${waypointDisplayName(w)}`;
    button.title=t('drive.makeNextTarget');
    button.addEventListener('click',()=>{
      setActiveIndex(i);
      buildManualLegToActive();
      panel.classList.remove('show');
      showToast(t('drive.nextPoint',{name:waypointDisplayName(w)}));
      render();
    });
    li.appendChild(button);
    waypointList.appendChild(li);
  });
}

function setActiveIndex(index) {
  activeIndex=Math.max(0,Math.min(waypointPixels.length-1,index));
  localStorage.setItem(STORAGE_PROGRESS,String(activeIndex));
  const waypoint=navigationWaypoints[activeIndex];
  if (waypoint) localStorage.setItem(STORAGE_TARGET, waypoint.loopClosure ? '__LOOP_CLOSURE__' : waypoint.game);
  refreshWaypointList();
}

function prepareDirectionalWaypoints({preserveTarget=null, preserveClosure=false} = {}) {
  navigationWaypoints=buildDirectionalLoop(route.waypoints,direction);
  rawWaypointPixels=navigationWaypoints.map(w=>hubToPixel(w.lat,w.lng));
  waypointPixels=rawWaypointPixels.map(p=>[...p]);
  waypointNodeIds=[];

  const storedTarget=localStorage.getItem(STORAGE_TARGET);
  const targetGame=preserveTarget || (storedTarget && storedTarget !== '__LOOP_CLOSURE__' ? storedTarget : null);
  const wantsClosure=preserveClosure || (!preserveTarget && storedTarget === '__LOOP_CLOSURE__');
  if (wantsClosure) activeIndex=navigationWaypoints.length-1;
  else if (targetGame) {
    const found=navigationWaypoints.findIndex(w=>!w.loopClosure && w.game===targetGame);
    if (found>=0) activeIndex=found;
  }
  if (activeIndex<0 || activeIndex>=navigationWaypoints.length) activeIndex=0;
  localStorage.setItem(STORAGE_PROGRESS,String(activeIndex));
  const activeWaypoint=navigationWaypoints[activeIndex];
  if (activeWaypoint) localStorage.setItem(STORAGE_TARGET, activeWaypoint.loopClosure ? '__LOOP_CLOSURE__' : activeWaypoint.game);
  refreshDirectionButton();
  refreshWaypointList();
}

function snapWaypointTargetsToRoad() {
  if (!roadGraph) return;
  waypointNodeIds=[];
  waypointPixels=rawWaypointPixels.map((pixel,i)=>{
    const waypoint=navigationWaypoints[i];
    const snapped=waypoint?.snapMode==='throughAsphalt'
      ? nearestSuitableRoadNode(pixel,roadGraph,{surface:'asphalt',minDegree:2})
      : nearestRoadNode(pixel,roadGraph);
    waypointNodeIds.push(snapped.id);
    // Requested pass-through landmarks are visibly moved onto the asphalt road.
    if (waypoint?.snapMode==='throughAsphalt' && snapped.id>=0) return [...roadGraph.nodes[snapped.id].pixel];
    return [...pixel];
  });
}

function optimizeRouteOrderWithGraph() {
  if (!roadGraph || waypointOrderOptimized || route?.routing?.optimizeFirstVisitOrder === false) return;
  const currentTarget = navigationWaypoints[activeIndex];
  const baseWaypoints = route.waypoints.map(w => ({...w}));
  const basePixels = baseWaypoints.map(w => hubToPixel(w.lat, w.lng));
  const baseNodeIds = basePixels.map((pixel, i) => {
    const waypoint = baseWaypoints[i];
    const snapped = waypoint?.snapMode === 'throughAsphalt'
      ? nearestSuitableRoadNode(pixel, roadGraph, {surface:'asphalt', minDegree:2})
      : nearestRoadNode(pixel, roadGraph);
    return snapped.id;
  });
  const settings = route.routing || {};
  const optimized = optimizeWaypointOrderByFirstVisit(basePixels, roadGraph, {
    loop:true,
    avoidDirt:settings.avoidDirt !== false,
    reusePenalty:Number.isFinite(settings.reusePenalty) ? settings.reusePenalty : 7,
    avoidImmediateBacktrack:settings.avoidImmediateBacktrack !== false,
    waypointNodeIds:baseNodeIds,
    maxIterations:Number.isFinite(settings.maxOrderIterations) ? settings.maxOrderIterations : 5,
  });
  const identity = optimized.order.every((value, i) => value === i);
  if (!identity) {
    optimizedMoveCount = optimized.order.filter((value, i) => value !== i).length;
    route.waypoints = optimized.order.map(i => baseWaypoints[i]);
  }
  waypointOrderOptimized = true;
  prepareDirectionalWaypoints({
    preserveTarget:currentTarget?.game || null,
    preserveClosure:Boolean(currentTarget?.loopClosure),
  });
}

function rebuildRoadRoute() {
  if (!directedRuntime) return;
  if (roadGraph) snapWaypointTargetsToRoad();
  else waypointPixels=rawWaypointPixels.map(p=>[...p]);
  const legs=[];
  const allPoints=[];
  for (let i=0;i<waypointPixels.length-1;i++) {
    const a=worldTargetForWaypoint(i), b=worldTargetForWaypoint(i+1);
    const result=routeBetweenWorldPoints(a,b,directedRuntime,{avoidDirt:true});
    const leg=directedResultToLeg(result,i+1);
    if (!leg || leg.points.length < 2) throw new Error(`could not connect directed leg ${i+1}`);
    legs.push({fromIndex:i,toIndex:i+1,...leg});
    if (!allPoints.length) allPoints.push(...leg.points);
    else allPoints.push(...leg.points.slice(1));
  }
  roadRoute={points:allPoints,legs};
  roadRoutePixels=allPoints;
  roadRoutingError='';
  if (car) buildManualLegToActive();
  const directionText=direction==='forward'?t('drive.clockwise'):t('drive.counterClockwise');
  document.getElementById('routeNote').textContent=t('drive.routeBuilt',{direction:directionText,count:route.waypoints.length,moves:optimizedMoveCount});
}

function plannerItemLabel(item) {
  if (!item) return t('drive.plannerStop');
  return localizedRouteItemName(item,drivePlacesById,getLocale()) || t('drive.plannerStop');
}

async function loadDrivePlaceCatalog(){
  try{
    const response=await fetch('/api/places?mode=all',{cache:'no-store'});
    if(!response.ok)throw new Error(`HTTP ${response.status}`);
    const payload=await response.json();
    drivePlacesById=new Map((payload?.places||[]).map(place=>[place.id,place]));
  }catch(err){
    drivePlacesById=new Map();
    console.warn('Place catalog unavailable for DRIVE labels',err);
  }
}

function plannerSessionActive(snapshot=plannerNavigation) {
  return Boolean(snapshot?.session && !snapshot.session.finished_at && snapshot.session.current_item_id);
}

function refreshPlannerWaypointList() {
  if (!plannerNavigation) return;
  waypointList.replaceChildren();
  for (const row of plannerProgressModel(plannerNavigation)) {
    const li=document.createElement('li');
    if (row.status==='active') li.classList.add('current');
    const button=document.createElement('button');
    button.type='button'; button.className='waypoint-select';
    const prefix=row.status==='visited'?'✓':row.status==='skipped'?'⊘':row.status==='active'?'▶':'·';
    button.textContent=`${prefix} ${row.index+1}. ${plannerItemLabel(row.item)}`;
    button.disabled=true;
    li.appendChild(button); waypointList.appendChild(li);
  }
}

function syncPlannerVisualState(snapshot, {announce=false}={}) {
  plannerNavigation=plannerSessionActive(snapshot) ? snapshot : null;
  plannerLeg=null; guidancePolyline=[]; rerouteState={pendingSince:null,shouldReroute:false};
  plannerCompletionBusy=false; plannerCompletionItemId=null;
  if (!plannerNavigation) {
    plannerRoutePixels=[]; plannerRouteMarkers=[];
    if (plannerSessionControls) plannerSessionControls.hidden=true;
    if (route) {
      document.getElementById('routeName').textContent=route.name;
      document.getElementById('routeNote').textContent=roadRoute?t('drive.routeBuilt',{direction:direction==='forward'?t('drive.clockwise'):t('drive.counterClockwise'),count:route.waypoints.length,moves:optimizedMoveCount}):t('drive.loadingRoutingOverlay');
      refreshWaypointList();
    }
    render(); return;
  }
  const geom=plannerNavigation.preview?.geometry || [];
  plannerRoutePixels=geom.map(p=>worldToPixel(Number(p[1]),Number(p[3])));
  const targetById=new Map((plannerNavigation.targets||[]).map(t=>[t.route_item_id,t]));
  plannerRouteMarkers=(plannerNavigation.route?.items||[]).map(item=>{
    const t=targetById.get(item.id); if(!t?.world)return null;
    return {id:item.id,pixel:worldToPixel(t.world.x,t.world.z)};
  }).filter(Boolean);
  document.getElementById('routeName').textContent=plannerNavigation.route?.name || t('common.route');
  document.getElementById('routeNote').textContent=t('drive.plannerLiveSync',{revision:plannerNavigation.route?.revision??'—'});
  if (plannerSessionControls) plannerSessionControls.hidden=false;
  refreshPlannerWaypointList();
  if (announce) showToast(t('drive.routeUpdated'));
  if (car && directedRuntime && currentDirectedMatch) buildPlannerGuidance({userUpdate:announce});
  render();
}

async function loadPlannerNavigationSession({announce=false}={}) {
  try {
    const response=await fetch('/api/navigation/active',{cache:'no-store'});
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const snapshot=await response.json();
    syncPlannerVisualState(snapshot,{announce});
    return snapshot;
  } catch (err) {
    console.warn('Planner navigation sync unavailable',err);
    return null;
  }
}

function plannerResultToLeg(result) {
  if (!result || !directedRuntime || !result.worldPoints?.length) return null;
  const points=result.worldPoints.map(p=>worldToPixel(p.x,p.z));
  return {segmentIds:result.segmentIds,segmentSet:new Set(result.segmentIds),points,maneuvers:routeManeuvers(result,points,directedRuntime),distanceM:result.distanceM};
}

function buildPlannerGuidance({reroute=false,userUpdate=false}={}) {
  plannerLeg=null;
  if (!plannerSessionActive() || !directedRuntime || !currentDirectedMatch) return false;
  if (reroute) { offRouteEl.textContent=t('drive.rerouting'); offRouteEl.classList.add('show'); }
  const result=plannerGuidanceFromMatch(currentDirectedMatch,plannerNavigation,directedRuntime,{avoidDirt:true});
  const leg=plannerResultToLeg(result);
  if (!leg || leg.points.length<2) { showNoLegalRoute(); return false; }
  plannerLeg=leg; routingFailClosed=false; rerouteState={pendingSince:null,shouldReroute:false};
  offRouteEl.classList.remove('show');
  if (userUpdate) showToast(t('drive.routeUpdated'));
  return true;
}

async function plannerNavigationAction(action) {
  const sid=plannerNavigation?.session?.id; if(!sid)return;
  try {
    const response=await fetch(`/api/navigation/${action}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:sid})});
    const snapshot=await response.json(); if(!response.ok)throw new Error(snapshot.detail||snapshot.error||`HTTP ${response.status}`);
    syncPlannerVisualState(snapshot);
    if (plannerSessionActive() && car && directedRuntime) buildPlannerGuidance({userUpdate:true});
  } catch(err){showToast(t('drive.navigationError',{error:String(err?.message||err)}),4200)}
}

async function maybeCompletePlannerTarget(distanceM) {
  const target=plannerNavigation?.current_target;
  if (!target || plannerCompletionBusy || plannerCompletionItemId===target.route_item_id) return;
  if (!shouldCompletePlannerItem({distanceM,matchSegmentId:currentDirectedMatch?.segmentId,guidance:plannerLeg})) return;
  plannerCompletionBusy=true; plannerCompletionItemId=target.route_item_id;
  try {
    const response=await fetch('/api/navigation/reached',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:plannerNavigation.session.id,route_item_id:target.route_item_id,distance_m:distanceM,on_legal_leg:true})});
    const snapshot=await response.json(); if(!response.ok)throw new Error(snapshot.detail||snapshot.error||`HTTP ${response.status}`);
    const next=snapshot?.current_target;
    if(next)showToast(t('drive.nextAfter',{name:plannerItemLabel((plannerNavigation.route?.items||[]).find(x=>x.id===target.route_item_id)),next:plannerItemLabel((snapshot.route?.items||[]).find(x=>x.id===next.route_item_id))}),3600);
    else showToast(t('drive.routeComplete'),4200);
    syncPlannerVisualState(snapshot);
  } catch(err){plannerCompletionItemId=null;console.warn('Could not advance Planner stop',err)}
  finally{plannerCompletionBusy=false}
}

function updatePlannerNavigation(packet,pixel,headingDeg) {
  if (!plannerSessionActive()) return false;
  if (!plannerLeg || !plannerLeg.segmentSet?.has(currentDirectedMatch?.segmentId)) {
    if (!plannerLeg) buildPlannerGuidance();
  }
  const target=plannerNavigation.current_target;
  if (!target?.world) return true;
  let distanceM=Math.hypot(packet.positionX-target.world.x,packet.positionZ-target.world.z);
  let guidanceTarget=worldToPixel(target.world.x,target.world.z),offM=null,upcomingManeuver=null;
  guidancePolyline=[];
  if (plannerLeg?.points?.length>1) {
    const progress=nearestPolylineProgress(pixel,plannerLeg.points);
    guidancePolyline=remainingPolylinePoints(plannerLeg.points,progress);
    const roadDistance=pixelsToWorldMeters(remainingPolylineDistancePx(plannerLeg.points,progress));
    guidanceTarget=pointAheadOnPolyline(plannerLeg.points,progress,220*PX_PER_WORLD_M);
    offM=pixelsToWorldMeters(progress.distancePx);
    upcomingManeuver=nextManeuver(plannerLeg.maneuvers||[],plannerLeg.points,progress,{passedTolerancePx:12*PX_PER_WORLD_M});
    distanceEl.textContent=roadDistance>=1000?t('drive.routeDistanceKm',{distance:(roadDistance/1000).toFixed(1)}):t('drive.routeDistanceMeters',{distance:Math.round(roadDistance)});
  } else {
    distanceEl.textContent=distanceM>=1000?t('drive.directDistanceKm',{distance:(distanceM/1000).toFixed(1)}):t('drive.directDistanceMeters',{distance:Math.round(distanceM)});
  }
  setTurnUI(upcomingManeuver);
  const items=plannerNavigation.route?.items||[], currentId=plannerNavigation.session.current_item_id;
  const idx=Math.max(0,items.findIndex(x=>x.id===currentId));
  nextTitle.textContent=plannerItemLabel(items[idx]);
  nextGame.textContent=`${t('drive.plannerRoute')} · ${plannerNavigation.route?.name||t('common.route')}`;
  progressEl.textContent=`${idx+1}/${items.length}`;
  navArrowSvg.style.transform=`rotate(${normalizeDeg(bearingDeg(pixel,guidanceTarget)-headingDeg)}deg)`;
  appendRecording(pixel);
  if (offM!==null && directedRuntime && currentDirectedMatch) {
    const offRoute=offM>OFF_ROUTE_METERS;
    rerouteState=nextRerouteState(rerouteState,{offRoute,confidence:currentDirectedMatch.confidence,nowMs:performance.now(),confirmMs:REROUTE_CONFIRM_MS,minConfidence:REROUTE_MIN_CONFIDENCE});
    if (rerouteState.shouldReroute) buildPlannerGuidance({reroute:true});
    else if(!routingFailClosed){offRouteEl.classList.toggle('show',offRoute);if(offRoute)offRouteEl.textContent=t('drive.offDirectedRoute',{distance:Math.round(offM)});}
  } else if(!routingFailClosed) offRouteEl.classList.remove('show');
  maybeCompletePlannerTarget(distanceM);
  if(follow)center=[pixel[0],pixel[1]];
  render(); return true;
}

function subscribePlannerDriveEvents() {
  if (plannerEvents) return;
  plannerEvents=new EventSource('/api/events');
  plannerEvents.addEventListener('route.updated',e=>{
    try { const p=JSON.parse(e.data); if(plannerNavigation?.session?.route_id===p.route_id)loadPlannerNavigationSession({announce:true}); } catch {}
  });
  plannerEvents.addEventListener('navigation.updated',()=>loadPlannerNavigationSession());
}

function updateTelemetryUI(payload) {
  const p=payload.packet;
  const connected=Boolean(payload.connected && p);
  connDot.classList.toggle('on',connected);
  connText.textContent=connected?`FH6 · ${payload.sourceIp||'UDP'}`:t('drive.waitingForza');
  if (!p) return;
  speedEl.textContent=Math.max(0,Math.round(p.speedKmh || 0));
  gearEl.textContent=formatGear(p.gear);
  rpmText.textContent=`${Math.max(0,Math.round(p.rpm||0))} RPM`;
  rpmBar.style.width=`${Math.max(0,Math.min(100,(p.rpm||0)/9000*100))}%`;
}

function appendRecording(pixel) {
  if (!recording) return;
  const last=recordBuffer.at(-1);
  if (!last || pixelsToWorldMeters(Math.hypot(pixel[0]-last[0],pixel[1]-last[1])) >= RECORD_SPACING_METERS) {
    recordBuffer.push([pixel[0],pixel[1]]);
    if (recordBuffer.length % 25 === 0) saveRecordedTrack(recordBuffer);
  }
}

function applyAutoZoom(speedKmh) {
  if (!autoZoomEnabled) {
    autoZoomActive = false;
    autoZoomRestoreZoom = null;
    return;
  }
  const state = nextAutoZoomState({
    speedKmh,
    follow,
    zoom,
    active:autoZoomActive,
    savedZoom:autoZoomRestoreZoom,
    maxZoom:VIEW_MAX_ZOOM,
    engageBelow:40,
    releaseAbove:45,
  });
  zoom = state.zoom;
  autoZoomActive = state.active;
  autoZoomRestoreZoom = state.savedZoom;
}

function updateNavigation(packet) {
  if (!route || !packet) return;
  if (!Number.isFinite(packet.positionX) || !Number.isFinite(packet.positionZ)) return;
  if (packet.positionX===0 && packet.positionZ===0) return;
  const pixel=worldToPixel(packet.positionX,packet.positionZ);
  applyAutoZoom(packet.speedKmh);
  const headingDeg=normalizeDeg((packet.yaw||0)*180/Math.PI);
  car={pixel,world:[packet.positionX,packet.positionZ],headingDeg};
  if (directedRuntime) {
    currentDirectedMatch=matchDirectedSegment(
      {x:packet.positionX,z:packet.positionZ}, headingDeg, directedRuntime, previousDirectedSegmentId
    );
    if (currentDirectedMatch?.confidence >= REROUTE_MIN_CONFIDENCE) previousDirectedSegmentId=currentDirectedMatch.segmentId;
  }

  if (plannerSessionActive() && updatePlannerNavigation(packet,pixel,headingDeg)) return;

  if (firstTelemetry) {
    firstTelemetry=false;
    if (activeIndex<0 || activeIndex>=waypointPixels.length) {
      const nearest=nearestWaypointIndex(pixel,waypointPixels);
      const d=pixelsToWorldMeters(Math.hypot(pixel[0]-waypointPixels[nearest][0],pixel[1]-waypointPixels[nearest][1]));
      setActiveIndex(d<700 && nearest<waypointPixels.length-1 ? nearest+1 : Math.max(0,nearest));
    }
  }

  if (firstTelemetry === false && directedRuntime && !manualLeg && !routingFailClosed) buildManualLegToActive();

  const reachPx=REACH_METERS*PX_PER_WORLD_M;
  const advanced=maybeAdvanceLoopWaypoint(pixel,waypointPixels,activeIndex,reachPx,Boolean(route.loop));
  if (advanced!==activeIndex) {
    manualLeg=null;
    setActiveIndex(advanced);
    buildManualLegToActive();
    showToast(t('drive.nextPoint',{name:waypointDisplayName(navigationWaypoints[advanced])}));
  }

  const target=waypointPixels[activeIndex];
  const targetWorld=pixelToWorld(target[0],target[1]);
  let distanceM=Math.hypot(packet.positionX-targetWorld[0],packet.positionZ-targetWorld[1]);
  let guidanceTarget=target;
  let offM=null;
  let upcomingManeuver=null;

  // A manually selected target gets a temporary road leg from the car's current position.
  // Otherwise target N follows the prebuilt scenic leg N-1.
  const guidanceLeg = manualLeg?.toIndex===activeIndex
    ? manualLeg
    : (roadRoute && activeIndex > 0 ? roadRoute.legs[activeIndex-1] : null);
  guidancePolyline=[];
  if (guidanceLeg && guidanceLeg.points.length > 1) {
    const progress=nearestPolylineProgress(pixel,guidanceLeg.points);
    guidancePolyline=remainingPolylinePoints(guidanceLeg.points,progress);
    distanceM=pixelsToWorldMeters(remainingPolylineDistancePx(guidanceLeg.points,progress));
    guidanceTarget=pointAheadOnPolyline(guidanceLeg.points,progress,220*PX_PER_WORLD_M);
    offM=pixelsToWorldMeters(progress.distancePx);
    upcomingManeuver=nextManeuver(guidanceLeg.maneuvers || [],guidanceLeg.points,progress,{passedTolerancePx:12*PX_PER_WORLD_M});
  }
  setTurnUI(upcomingManeuver);

  const w=navigationWaypoints[activeIndex];
  nextTitle.textContent=waypointDisplayName(w);
  nextGame.textContent=t('common.officialGame');
  distanceEl.textContent=guidanceLeg?(distanceM>=1000?t('drive.routeDistanceKm',{distance:(distanceM/1000).toFixed(1)}):t('drive.routeDistanceMeters',{distance:Math.round(distanceM)})):(distanceM>=1000?t('drive.directDistanceKm',{distance:(distanceM/1000).toFixed(1)}):t('drive.directDistanceMeters',{distance:Math.round(distanceM)}));
  progressEl.textContent=`${activeIndex+1}/${waypointPixels.length}`;
  const targetBearing=bearingDeg(pixel,guidanceTarget);
  navArrowSvg.style.transform=`rotate(${normalizeDeg(targetBearing-headingDeg)}deg)`;

  appendRecording(pixel);

  if (offM === null && recordedTrack.length>1 && !recording) {
    offM=pixelsToWorldMeters(nearestPolylineDistancePx(pixel,recordedTrack));
  }
  if (offM !== null && !recording && directedRuntime && currentDirectedMatch) {
    const offRoute=offM>OFF_ROUTE_METERS;
    rerouteState=nextRerouteState(rerouteState,{
      offRoute, confidence:currentDirectedMatch.confidence, nowMs:performance.now(),
      confirmMs:REROUTE_CONFIRM_MS, minConfidence:REROUTE_MIN_CONFIDENCE,
    });
    if (rerouteState.shouldReroute) {
      buildManualLegToActive({reroute:true});
    } else if (!routingFailClosed) {
      offRouteEl.classList.toggle('show',offRoute);
      if (offRoute) offRouteEl.textContent=t('drive.offDirectedRoute',{distance:Math.round(offM)});
    }
  } else if (!routingFailClosed) offRouteEl.classList.remove('show');

  if (follow) center=[pixel[0],pixel[1]];
  render();
}

async function pollTelemetry() {
  if (pollBusy) return;
  pollBusy=true;
  try {
    const r=await fetch('/api/telemetry',{cache:'no-store'});
    const payload=await r.json();
    updateTelemetryUI(payload);
    if (payload.connected && payload.packet) updateNavigation(payload.packet);
  } catch {
    connDot.classList.remove('on');connText.textContent=t('drive.serverUnavailable');
  } finally { pollBusy=false; }
}

async function loadRoadRoute() {
  const noteEl=document.getElementById('routeNote');
  noteEl.textContent=t('drive.loadingRoutingOverlay');
  // LabsGG is intentionally non-authoritative: overlay + POI ordering only.
  try {
    const response=await fetch('/api/roads',{cache:'no-store'});
    const dataset=await response.json();
    if (response.ok && Array.isArray(dataset.roads) && dataset.roads.length) {
      roadGraph=buildRoadGraph(dataset.roads);
      roadBuckets=buildRoadBuckets(roadGraph);
      optimizeRouteOrderWithGraph();
      snapWaypointTargetsToRoad();
    }
  } catch (err) {
    roadGraph=null; roadBuckets=new Map();
    console.warn('LabsGG overlay unavailable',err);
  }

  try {
    const response=await fetch('/api/navgraph',{cache:'no-store'});
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const dataset=await response.json();
    directedRuntime=buildDirectedRuntime(dataset);
    setRoutingStatus(
      dataset.capabilities?.route_validated?t('drive.routingValidated'):t('drive.routingReady'),
      'ok'
    );
    rebuildRoadRoute();
    if (plannerSessionActive() && car) buildPlannerGuidance();
    routingFailClosed=false;
    render();
  } catch (err) {
    directedRuntime=null; roadRoute=null; roadRoutePixels=[]; manualLeg=null; guidancePolyline=[];
    roadRoutingError=String(err?.message || err);
    setRoutingStatus(t('drive.routingUnavailable'),'error');
    noteEl.textContent=t('drive.routingUnavailableNote',{error:roadRoutingError});
    showNoLegalRoute();
    setTurnUI(null); render();
  }
}

async function init() {
  applyTranslations(document);
  bindLocaleFlagMenu(document.getElementById('driveLocaleButton'),document.getElementById('driveLocaleMenu'));
  installTooltips(document);
  await loadPlaceNames();
  await loadDrivePlaceCatalog();
  const rr=await fetch('/route.json',{cache:'no-store'});
  route=await rr.json();
  prepareDirectionalWaypoints();
  document.getElementById('routeName').textContent=route.name;
  document.getElementById('routeNote').textContent=t('drive.loadingRoutingOverlay');
  if (activeIndex<0 || activeIndex>=waypointPixels.length) activeIndex=0;
  refreshWaypointList();
  refreshDirectionButton();
  // Start focused on Hirosaki immediately; road routing loads in the background.
  center=[...waypointPixels[0]]; zoom=12; follow=true;
  document.getElementById('followBtn').classList.add('active');
  roadsBtn.classList.toggle('active',roadLayerVisible);
  refreshAutoZoomButton();
  render();
  pollTelemetry();
  setInterval(pollTelemetry,50);
  loadRoadRoute();
  subscribePlannerDriveEvents();
  loadPlannerNavigationSession();
}

window.addEventListener('fh6:localechange',()=>{
  applyTranslations(document);
  refreshAutoZoomButton();
  refreshDirectionButton();
  plannerSessionActive()?refreshPlannerWaypointList():refreshWaypointList();
  refreshCurrentTargetCopy();
  if(plannerSessionActive())document.getElementById('routeNote').textContent=t('drive.plannerLiveSync',{revision:plannerNavigation.route?.revision??'—'});
  else if(roadRoute&&route)document.getElementById('routeNote').textContent=t('drive.routeBuilt',{direction:direction==='forward'?t('drive.clockwise'):t('drive.counterClockwise'),count:route.waypoints.length,moves:optimizedMoveCount});
  else document.getElementById('routeNote').textContent=t('drive.loadingRoutingOverlay');
  if(routingFailClosed)showNoLegalRoute();
  setTurnUI(currentManeuver);
  render();
});

// Map controls
roadsBtn.addEventListener('click',()=>{
  roadLayerVisible=!roadLayerVisible;
  localStorage.setItem(STORAGE_ROADS_VISIBLE,roadLayerVisible?'1':'0');
  roadsBtn.classList.toggle('active',roadLayerVisible);
  refreshAutoZoomButton();
  render();
});
document.getElementById('zoomIn').addEventListener('click',()=>zoomBy(1));
document.getElementById('zoomOut').addEventListener('click',()=>zoomBy(-1));
document.getElementById('fitBtn').addEventListener('click',fitRoute);
document.getElementById('followBtn').addEventListener('click',()=>{
  follow=!follow; document.getElementById('followBtn').classList.toggle('active',follow);
  if (follow && car) { center=[...car.pixel]; render(); }
});

autoZoomBtn.addEventListener('click',()=>{
  autoZoomEnabled=!autoZoomEnabled;
  localStorage.setItem(STORAGE_AUTO_ZOOM, autoZoomEnabled ? '1' : '0');
  if (!autoZoomEnabled && autoZoomActive) {
    if (Number.isFinite(autoZoomRestoreZoom)) zoom = autoZoomRestoreZoom;
    autoZoomActive = false;
    autoZoomRestoreZoom = null;
    render();
  }
  refreshAutoZoomButton();
});
plannerSkipStop?.addEventListener('click',()=>plannerNavigationAction('skip'));
plannerPreviousStop?.addEventListener('click',()=>plannerNavigationAction('previous'));
document.getElementById('menuBtn').addEventListener('click',()=>panel.classList.toggle('show'));

directionBtn.addEventListener('click',()=>{
  const oldTarget=navigationWaypoints[activeIndex];
  direction=direction==='forward' ? 'reverse' : 'forward';
  localStorage.setItem(STORAGE_DIRECTION,direction);
  manualLeg=null;
  guidancePolyline=[];
  prepareDirectionalWaypoints({
    preserveTarget:oldTarget?.game || null,
    preserveClosure:Boolean(oldTarget?.loopClosure),
  });
  try {
    if (directedRuntime) rebuildRoadRoute();
    showToast(t('drive.directionChanged',{direction:direction==='forward'?t('drive.clockwise'):t('drive.counterClockwise')}));
  } catch (err) {
    showToast(t('drive.directionFailed',{error:String(err?.message||err)}),4500);
  }
  render();
});

function updateRecordButtons() {
  for (const id of ['recordBtn','panelRecord']) {
    const btn=document.getElementById(id);
    if (btn) btn.classList.toggle('active',recording);
  }
}

function toggleRecording() {
  if (!recording) {
    if(recordedTrack.length>1&&!confirm(t('drive.recordReplaceConfirm')))return;
    recordBuffer=[];
    recording=true;
    updateRecordButtons();
    showToast(t('drive.recordingStarted'),4000);
  } else {
    recording=false;
    updateRecordButtons();
    if(recordBuffer.length>2){saveRecordedTrack(recordBuffer);showToast(t('drive.recordingStopped',{count:recordBuffer.length}),3500)}
    else showToast(t('drive.recordingTooShort'));
    render();
  }
}

document.getElementById('recordBtn').addEventListener('click',toggleRecording);
document.getElementById('panelRecord').addEventListener('click',toggleRecording);
document.getElementById('panelZoomIn').addEventListener('click',()=>zoomBy(1));
document.getElementById('panelZoomOut').addEventListener('click',()=>zoomBy(-1));
document.getElementById('panelFit').addEventListener('click',()=>{ fitRoute(); panel.classList.remove('show'); });

document.getElementById('resetProgress').addEventListener('click',()=>{ manualLeg=null; guidancePolyline=[]; setActiveIndex(0); if(car&&directedRuntime) buildManualLegToActive(); showToast(t('drive.progressReset')); render(); });
document.getElementById('clearTrack').addEventListener('click',()=>{
  if(!recordedTrack.length||confirm(t('drive.clearTrackConfirm'))){recordedTrack=[];localStorage.removeItem(STORAGE_TRACK);showToast(t('drive.recordingCleared'));render()}
});
document.getElementById('exportTrack').addEventListener('click',()=>{
  if(recordedTrack.length<2){showToast(t('drive.exportNeedsTrack'));return}
  const blob=new Blob([JSON.stringify({format:'fh6-scenic-track-v1',points:recordedTrack},null,2)],{type:'application/json'});
  const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='FH6_Grand_Tour_recorded_route.json'; a.click(); setTimeout(()=>URL.revokeObjectURL(a.href),1000);
});
document.getElementById('importTrack').addEventListener('click',()=>document.getElementById('trackFile').click());
document.getElementById('trackFile').addEventListener('change',async e=>{
  const file=e.target.files?.[0]; if (!file) return;
  try {
    const obj=JSON.parse(await file.text()); const points=Array.isArray(obj)?obj:obj.points;
    if (!Array.isArray(points) || points.length<2 || points.some(p=>!Array.isArray(p)||p.length!==2||!p.every(Number.isFinite))) throw new Error('bad format');
    saveRecordedTrack(points);showToast(t('drive.trackImported',{count:points.length}));render();
  } catch {showToast(t('drive.trackImportFailed'))}
  e.target.value='';
});

mapEl.addEventListener('wheel',e=>{ e.preventDefault(); zoomBy(e.deltaY<0?1:-1,e.offsetX,e.offsetY); },{passive:false});
mapEl.addEventListener('pointerdown',e=>{
  if (e.button!==0) return; mapEl.setPointerCapture(e.pointerId); drag={id:e.pointerId,x:e.clientX,y:e.clientY,start:[...center]}; mapEl.classList.add('dragging');
});
mapEl.addEventListener('pointermove',e=>{
  if (!drag || drag.id!==e.pointerId) return;
  const s=scaleForZoom(); center=[drag.start[0]-(e.clientX-drag.x)*s,drag.start[1]-(e.clientY-drag.y)*s];
  follow=false; document.getElementById('followBtn').classList.remove('active'); render();
});
function endDrag(e){ if(drag&&drag.id===e.pointerId){drag=null;mapEl.classList.remove('dragging');} }
mapEl.addEventListener('pointerup',endDrag); mapEl.addEventListener('pointercancel',endDrag);
window.addEventListener('resize',render);

init().catch(err=>{console.error(err);connText.textContent=t('drive.loadRouteError');showToast(`${t('drive.loadRouteError')}: ${String(err)}`,5000)});
