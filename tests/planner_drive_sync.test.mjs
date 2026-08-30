import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {buildDirectedRuntime,matchDirectedSegment} from '../static/directed_nav.js';
import {plannerGuidanceFromMatch,plannerProgressModel,shouldCompletePlannerItem} from '../static/planner_drive.js';

function payload(){return {format:'fh6-navgraph-v1',capabilities:{directed_segments:true,turn_transitions:true,route_validated:true},points:[[0,0,0,0],[1,100,0,0],[2,200,0,0],[3,100,0,100],[4,200,0,100]],segments:[[0,0,0,1,100,1,'asphalt'],[1,0,1,2,100,1,'asphalt'],[2,1,1,3,100,0,'asphalt'],[3,2,3,4,100,1,'asphalt']],transitions:[[0,1],[0,2],[2,3]]};}

test('planner ordinary target uses legal directed route from current match',()=>{
 const rt=buildDirectedRuntime(payload(),{bucketSize:100}); const match=matchDirectedSegment({x:20,z:0},90,rt);
 const snap={current_target:{route_item_id:'i1',world:{x:200,z:100},fixed_segment_ids:[]}};
 const r=plannerGuidanceFromMatch(match,snap,rt); assert.deepEqual(r.segmentIds,[0,2,3]);
});

test('planner scenic target preserves fixed block instead of shortcutting it',()=>{
 const rt=buildDirectedRuntime(payload(),{bucketSize:100}); const match=matchDirectedSegment({x:20,z:0},90,rt);
 // entry=1, fixed scenic path must go 1->3->4 even though 1->2 is another legal continuation.
 const snap={current_target:{route_item_id:'s',entry_world:{x:100,z:0},world:{x:200,z:100},fixed_segment_ids:[2,3]}};
 const r=plannerGuidanceFromMatch(match,snap,rt); assert.deepEqual(r.segmentIds,[0,2,3]);
});

test('progress model preserves visited skipped and active item',()=>{
 const snap={route:{items:[{id:'a'},{id:'b'},{id:'c'}]},session:{current_item_id:'c'},progress:[{route_item_id:'a',status:'visited'},{route_item_id:'b',status:'skipped'},{route_item_id:'c',status:'active'}]};
 assert.deepEqual(plannerProgressModel(snap).map(x=>x.status),['visited','skipped','active']);
});

test('completion requires target within 50m and current match on legal guidance leg',()=>{
 const g={segmentIds:[4,8,9]};
 assert.equal(shouldCompletePlannerItem({distanceM:49,matchSegmentId:8,guidance:g}),true);
 assert.equal(shouldCompletePlannerItem({distanceM:51,matchSegmentId:8,guidance:g}),false);
 assert.equal(shouldCompletePlannerItem({distanceM:20,matchSegmentId:7,guidance:g}),false);
});

test('drive subscribes to planner route/session changes without legacy shortestPath fallback',()=>{
 const app=fs.readFileSync(new URL('../static/app.js',import.meta.url),'utf8');
 const html=fs.readFileSync(new URL('../static/index.html',import.meta.url),'utf8');
 assert.match(app,/planner_drive\.js/);
 assert.match(app,/\/api\/navigation\/active/);
 assert.match(app,/route\.updated/);
 assert.match(app,/navigation\.updated/);
 assert.match(app,/t\('drive\.routeUpdated'\)/);
 assert.match(html,/id="plannerSkipStop"/); assert.match(html,/id="plannerPreviousStop"/);
 const plannerSection=app.slice(app.indexOf('loadPlannerNavigationSession'));
 assert.doesNotMatch(plannerSection,/shortestPath\s*\(/);
});

test('planner start button creates navigation session and opens named drive window',()=>{
 const planner=fs.readFileSync(new URL('../static/planner/planner.js',import.meta.url),'utf8');
 const api=fs.readFileSync(new URL('../static/planner/api.js',import.meta.url),'utf8');
 assert.match(api,/navigationStart/);
 assert.match(api,/\/api\/navigation\/start/);
 assert.match(planner,/navigationStart/);
 assert.match(planner,/window\.open\([^\n]*fh6-drive/);
 assert.doesNotMatch(planner,/Navigation sessions are enabled in the next integration phase/);
});
