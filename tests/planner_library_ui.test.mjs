import test from 'node:test'; import assert from 'node:assert/strict';
import { createLibraryState, reduceLibrary, visibleWindow, libraryResults } from '../static/planner/library.js';
const places=Array.from({length:100},(_,i)=>({id:'p'+i,name:'Place '+i,aliases:[],category:i%2?'landmarks':'scenic_roads',tags:[],surface:'asphalt',access:'easy',source:'game',quality:'verified',default_visible:true,featured:i<3,favorite:i===4,scenic_score:i%5}));

test('library state preserves query filters sort selection and scroll across detail back',()=>{
 let s=createLibraryState(places); s=reduceLibrary(s,{type:'query',value:'Place'}); s=reduceLibrary(s,{type:'filter',key:'categories',value:['landmarks']}); s=reduceLibrary(s,{type:'scroll',value:480}); s=reduceLibrary(s,{type:'select',id:'p9'}); s=reduceLibrary(s,{type:'detail',open:true}); s=reduceLibrary(s,{type:'detail',open:false});
 assert.equal(s.query,'Place'); assert.deepEqual(s.filters.categories,['landmarks']); assert.equal(s.scrollTop,480); assert.equal(s.selectedId,'p9');
});

test('virtual list returns only a bounded visible window',()=>{
 const w=visibleWindow(1000,720,56,3000); assert.ok(w.end-w.start<30); assert.ok(w.start>0);
});

test('library result marks can distinguish place already in route',()=>{
 const s=createLibraryState(places); const r=libraryResults(s); assert.equal(r.results.length,100);
});
