import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const read=p=>fs.readFileSync(new URL(p,import.meta.url),'utf8');

test('planner shell is map-first with filters map route and global search',()=>{
  const html=read('../static/planner/index.html');
  assert.match(html,/id="placeSearch"/);
  assert.match(html,/MAP FILTERS/);
  assert.match(html,/id="layerGroups"/);
  assert.match(html,/id="layersRecommended"/);
  assert.match(html,/id="layersEnableAll"/);
  assert.match(html,/id="layersDisableAll"/);
  assert.match(html,/id="layersCollapseAll"/);
  assert.match(html,/id="layersExpandAll"/);
  assert.match(html,/id="plannerMap"/);
  assert.match(html,/id="routePanel"/);
  assert.doesNotMatch(html,/id="placesList"/);
  assert.doesNotMatch(html,/id="placeDetails"/);
});

test('place selection stays on map in anchored popover and search results float over map',()=>{
  const html=read('../static/planner/index.html');
  const mapStart=html.indexOf('id="plannerMap"');
  const mapEnd=html.indexOf('</section>',mapStart);
  const map=html.slice(mapStart,mapEnd);
  assert.match(map,/id="placePopover"/);
  assert.match(map,/id="searchResults"/);
});

test('planner controller uses full catalog layers and popover modules',()=>{
  const js=read('../static/planner/planner.js');
  assert.match(js,/\.\/layers\.js/);
  assert.match(js,/\.\/popover\.js/);
  assert.match(js,/api\.places\(['"]all['"]\)/);
  assert.match(js,/localStorage/);
  assert.match(js,/layerGroups/);
  assert.doesNotMatch(js,/renderDetails\s*\(/);
});


test('planner exposes DRIVE PLAN mode switch with PLAN active',()=>{
  const html=read('../static/planner/index.html');
  assert.match(html,/class="[^"]*hc-mode[^"]*"[^>]*>[\s\S]*href="\/"[^>]*>DRIVE<[\s\S]*<strong[^>]*>PLAN<\/strong>/);
});

test('Planner visibly identifies v1.19.2 so stale-server launches are obvious',()=>{
  const html=read('../static/planner/index.html');
  assert.match(html,/v1\.19\.2/);
});

test('planner uses thumbnail in search and lazy non-draggable local media',()=>{
  const js=read('../static/planner/planner.js');
  assert.match(js,/localPlaceImagePath\(p,'thumb'\)/);
  assert.match(js,/img\.loading='lazy'/);
  assert.match(js,/img\.decoding='async'/);
  assert.match(js,/img\.draggable=false/);
  assert.match(js,/isPlaceRoutable/);
});
