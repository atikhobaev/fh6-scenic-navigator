import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
const html=fs.readFileSync(new URL('../static/planner/index.html',import.meta.url),'utf8');
const js=fs.readFileSync(new URL('../static/planner/planner.js',import.meta.url),'utf8');
const api=fs.readFileSync(new URL('../static/planner/api.js',import.meta.url),'utf8');
test('planner menu exposes versioned user and route import export',()=>{
 for(const id of ['plannerMenuBtn','exportUserData','importUserData','exportRoute','importRoute','backupFile','routeFile'])assert.match(html,new RegExp(`id="${id}"`));
 for(const name of ['backupExport','backupImport','routeExport','routeImport'])assert.match(api,new RegExp(name));
 assert.match(js,/fh6-navigator-backup\.json/);assert.match(js,/\.fh6route/);
});
test('advanced diagnostics expose navigation anchors and directed graph toggles',()=>{
 assert.match(html,/id="showNavAnchors"/);assert.match(html,/id="showDirectedGraph"/);assert.match(api,/diagnostics/);assert.match(api,/navgraph/);
 assert.match(js,/setDiagnostics/);
});
