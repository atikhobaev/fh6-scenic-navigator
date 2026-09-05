import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const html = fs.readFileSync(new URL('../static/index.html', import.meta.url), 'utf8');
const css = fs.readFileSync(new URL('../static/styles/app.css', import.meta.url), 'utf8');

test('map UI contains a toggleable road-surface canvas', () => {
  assert.match(html, /id="roadsCanvas"/);
  assert.match(html, /id="roadsBtn"/);
});

test('navigation card has dedicated next-turn instruction fields', () => {
  assert.match(html, /id="turnIcon"/);
  assert.match(html, /id="turnInstruction"/);
  assert.match(html, /id="turnDistance"/);
});

test('toolbar is single-row and burger menu is never wrapped by the tools container', () => {
  assert.match(css, /\.drive-tools\s*\{[^}]*flex-wrap:\s*nowrap/s);
  assert.match(html, /id="menuBtn"/);
});

test('route panel exposes direction switching and clickable waypoint selection', () => {
  assert.match(html, /id="directionBtn"/);
  assert.match(appJs, /waypoint-select/);
});

test('compact toolbar actions remain available inside the burger panel', () => {
  for (const id of ['panelZoomIn','panelZoomOut','panelFit','panelRecord']) {
    assert.match(html, new RegExp(`id="${id}"`));
  }
});


test('top toolbar includes an explicit auto-zoom toggle and tooltips for compact buttons', () => {
  assert.match(html, /id="autoZoomBtn"/);
  assert.match(html, /id="zoomIn"[^>]*data-i18n-title="drive.zoomIn"/);
  assert.match(html, /id="zoomOut"[^>]*data-i18n-title="drive.zoomOut"/);
  assert.match(html, /id="roadsBtn"[^>]*data-i18n-title="drive.roadsTooltip"/);
  assert.match(html, /id="followBtn"[^>]*data-i18n-title="drive.followTooltip"/);
  assert.match(html, /id="fitBtn"[^>]*data-i18n-title="drive.fitRouteTooltip"/);
  assert.match(html, /id="recordBtn"[^>]*data-i18n-title="drive.recordTooltip"/);
  assert.match(html, /id="menuBtn"[^>]*data-i18n-title="drive.menuTooltip"/);
});

const appJs = fs.readFileSync(new URL('../static/app.js', import.meta.url), 'utf8');

test('yellow guidance overlay is driven by the current remaining guidance route, not only a manual selection', () => {
  assert.match(appJs, /let\s+guidancePolyline\s*=\s*\[\]/);
  assert.match(appJs, /points:\s*pointsAttr\(guidancePolyline\)/);
  assert.doesNotMatch(appJs, /points:\s*pointsAttr\(manualLeg\.points\)/);
});

test('turn card has three visible alert animation levels with reduced-motion fallback', () => {
  assert.match(css, /\.drive-turncard\.alert-far/);
  assert.match(css, /\.drive-turncard\.alert-near/);
  assert.match(css, /\.drive-turncard\.alert-urgent/);
  assert.match(css, /prefers-reduced-motion:\s*reduce/);
});

test('turn UI derives its flashing level from turn distance', () => {
  assert.match(appJs, /turnAlertLevel\(meters\)/);
  assert.match(appJs, /alert-far/);
  assert.match(appJs, /alert-near/);
  assert.match(appJs, /alert-urgent/);
});


test('auto zoom app thresholds are 40 and 45 kmh', () => {
  assert.match(appJs, /engageBelow:\s*40/);
  assert.match(appJs, /releaseAbove:\s*45/);
});

test('the turn arrow itself pulses at all three warning distances', () => {
  assert.match(css, /\.drive-turncard\.alert-far\s+\.drive-turn-icon/);
  assert.match(css, /\.drive-turncard\.alert-near\s+\.drive-turn-icon/);
  assert.match(css, /\.drive-turncard\.alert-urgent\s+\.drive-turn-icon/);
});

test('road graph load refines waypoint order before the final scenic route is built', () => {
  assert.match(appJs, /optimizeWaypointOrderByFirstVisit/);
  assert.match(appJs, /optimizeRouteOrderWithGraph\(\)/);
  const optimizeCall = appJs.indexOf('optimizeRouteOrderWithGraph();');
  const rebuildAfterLoad = appJs.indexOf('rebuildRoadRoute();', optimizeCall);
  assert.ok(optimizeCall >= 0 && rebuildAfterLoad > optimizeCall, 'optimizer should run before final route rebuild');
});

test('expanded itinerary uses a fresh progress-storage version so old waypoint indices do not target the wrong POI', () => {
  assert.match(appJs, /fh6-scenic-progress-v4/);
});

test('optimized itinerary persists the active POI by game id, not only by an order-dependent index', () => {
  assert.match(appJs, /fh6-scenic-target-v1/);
  assert.match(appJs, /localStorage\.setItem\(STORAGE_TARGET/);
  assert.match(appJs, /localStorage\.getItem\(STORAGE_TARGET\)/);
});


test('auto zoom has a dedicated toggle button with persistent state and immediate restore on disable', () => {
  assert.match(appJs, /STORAGE_AUTO_ZOOM/);
  assert.match(appJs, /localStorage\.getItem\(STORAGE_AUTO_ZOOM\)/);
  assert.match(appJs, /autoZoomBtn\.addEventListener\('click'/);
  assert.match(appJs, /if \(!autoZoomEnabled && autoZoomActive\)/);
  assert.match(appJs, /zoom = autoZoomRestoreZoom/);
  assert.match(appJs, /refreshAutoZoomButton\(\)/);
});

test('burger panel exposes authoritative WVAN routing status', () => {
  assert.match(html, /id="routingStatus"/);
  assert.match(appJs, /setRoutingStatus/);
  assert.match(appJs, /drive\.routingValidated/);
});

test('active guidance uses WVAN directed router and never legacy bidirectional shortestPath', () => {
  assert.match(appJs, /fetch\('\/api\/navgraph'/);
  assert.match(appJs, /buildDirectedRuntime\(dataset\)/);
  assert.match(appJs, /matchDirectedSegment/);
  assert.match(appJs, /routeFromMatch/);
  assert.match(appJs, /routeBetweenWorldPoints/);
  assert.doesNotMatch(appJs, /shortestPath\s*\(/);
  assert.doesNotMatch(appJs, /routeThroughWaypoints\s*\(/);
});

test('directed reroute is fail-closed and uses 45m 800ms confirmation', () => {
  assert.match(appJs, /OFF_ROUTE_METERS\s*=\s*45/);
  assert.match(appJs, /REROUTE_CONFIRM_MS\s*=\s*800/);
  assert.match(appJs, /t\('drive\.rerouting'\)/);
  assert.match(appJs, /t\('drive\.noLegalRoute'\)/);
});

const startBat = fs.readFileSync(new URL('../start.bat', import.meta.url), 'utf8');

test('launcher owns browser startup so an old 8080 server cannot be opened before the new build binds', () => {
  assert.match(startBat, /launcher\.py/i);
  assert.doesNotMatch(startBat, /Start-Process\s+'http:\/\/127\.0\.0\.1:8080'/i);
});

test('DRIVE visibly identifies the running build next to the mode switch', () => {
  assert.match(html, /v1\.20\.0/);
  assert.match(html, /class="[^"]*hc-mode[^"]*"[\s\S]*DRIVE[\s\S]*PLAN/);
});
