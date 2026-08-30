import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const html=fs.readFileSync(new URL('../static/planner/index.html',import.meta.url),'utf8');
const js=fs.readFileSync(new URL('../static/planner/planner.js',import.meta.url),'utf8');

test('route drawer separates Built-in and Saved routes',()=>{
  assert.match(js,/t\('planner\.routeGroupBuiltin'\),data\.built_in\|\|\[\]/);
  assert.match(js,/t\('planner\.routeGroupSaved'\),data\.routes\|\|\[\]/);
});

test('read-only built-in route explains edit-on-copy and disables rename',()=>{
  assert.match(html,/id="routeReadOnly"[^>]*>BUILT-IN · EDIT CREATES A COPY</);
  assert.match(js,/routeNameInput'\)\.disabled=Boolean\(state\.route\.read_only\)/);
  assert.match(js,/state\.route\.read_only/);
});

test('built-in route still uses normal preview and navigation APIs',()=>{
  assert.match(js,/api\.preview\(state\.route\.id/);
  assert.match(js,/api\.navigationStart\(state\.route\.id/);
});
