import test from 'node:test'; import assert from 'node:assert/strict'; import fs from 'node:fs';
const html=()=>fs.readFileSync(new URL('../static/planner/index.html',import.meta.url),'utf8');
const css=()=>fs.readFileSync(new URL('../static/planner/planner.css',import.meta.url),'utf8');
const drive=()=>fs.readFileSync(new URL('../static/index.html',import.meta.url),'utf8');
const app=()=>fs.readFileSync(new URL('../static/app.js',import.meta.url),'utf8');

test('planner has header and three persistent work areas',()=>{
  const s=html();
  for(const id of ['plannerHeader','libraryPanel','plannerMap','routePanel','routeNameInput','savedRoutesBtn','undoBtn','redoBtn','driveStatus']) assert.match(s,new RegExp(`id="${id}"`));
  assert.match(css(),/grid-template-columns/); assert.match(css(),/\.library-panel/); assert.match(css(),/\.route-panel/);
});

test('drive and planner expose the same DRIVE PLAN mode switch with the current mode active',()=>{
  const d=drive(), p=html();
  assert.match(d,/class="[^"]*hc-mode[^"]*"[^>]*>[\s\S]*<strong[^>]*>DRIVE<\/strong>[\s\S]*href="\/planner\/"[^>]*>PLAN</);
  assert.match(p,/class="[^"]*hc-mode[^"]*"[^>]*>[\s\S]*href="\/"[^>]*>DRIVE<[\s\S]*<strong[^>]*>PLAN<\/strong>/);
  assert.doesNotMatch(d,/id="plannerBtn"/);
  assert.doesNotMatch(d,/PLAN ROUTE/);
});

test('planner is modular and does not import drive app internals',()=>{
  const p=fs.readFileSync(new URL('../static/planner/planner.js',import.meta.url),'utf8');
  assert.doesNotMatch(p,/\.\.\/app\.js/); assert.match(p,/\.\/api\.js/); assert.match(p,/\.\/library\.js/); assert.match(p,/\.\/map\.js/); assert.match(p,/\.\/route_editor\.js/);
});
