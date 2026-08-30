import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const read=p=>fs.readFileSync(new URL(p,import.meta.url),'utf8');

test('add place flow offers map current-car and coordinates methods',()=>{
  const html=read('../static/planner/index.html');
  const app=read('../static/planner/planner.js');
  const api=read('../static/planner/api.js');
  for(const id of ['addPlaceDrawer','pickPlaceOnMap','placeAtCurrentCar','placeByCoordinates']) assert.match(html,new RegExp(`id="${id}"`));
  assert.match(api,/telemetry:\(\)=>request\('\/api\/telemetry'\)/);
  assert.match(app,/addPlaceMode/);
  assert.match(app,/placeAtCurrentCar/);
});

test('planner exposes resizable library and route panel handles',()=>{
  const html=read('../static/planner/index.html');
  const css=read('../static/planner/planner.css');
  const app=read('../static/planner/planner.js');
  assert.match(html,/id="libraryResizer"/);
  assert.match(html,/id="routeResizer"/);
  assert.match(css,/--library-width/);
  assert.match(css,/--route-width/);
  assert.match(app,/bindPanelResize/);
});
