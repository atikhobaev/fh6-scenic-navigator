import test from 'node:test';
import assert from 'node:assert/strict';
import { buildSearchIndex, searchPlaces, activeFilterChips } from '../static/planner/search.js';

const places=[
  {id:'a',name:'Hakone Nanamagari',aliases:['Hakone Mountain Road'],category:'scenic_roads',subcategory:'road',tags:['mountain','hairpins'],surface:'asphalt',access:'easy',source:'curated',quality:'reviewed',default_visible:true,featured:true,favorite:false,scenic_score:5},
  {id:'b',name:'Daikoku Parking Area',aliases:['Daikoku PA'],category:'landmarks',subcategory:'parking',tags:['city','night'],surface:'asphalt',access:'easy',source:'game',quality:'verified',default_visible:true,featured:false,favorite:true,scenic_score:4},
  {id:'c',name:'XP Board 12',aliases:[],category:'collectibles',subcategory:'board',tags:['board'],surface:'dirt',access:'normal',source:'game',quality:'verified',default_visible:false,featured:false,favorite:false,scenic_score:0},
  {id:'d',name:'My View',aliases:[],category:'my_place',subcategory:'',tags:[],surface:'unknown',access:'normal',source:'user',quality:'verified',default_visible:true,featured:false,favorite:false,scenic_score:0},
];

const idx=buildSearchIndex(places);

test('search uses aliases tags and tolerates a small typo',()=>{
  assert.equal(searchPlaces(idx,'mountain',{}).results[0].id,'a');
  assert.equal(searchPlaces(idx,'daikoko',{}).results[0].id,'b');
});

test('recommended hides default-invisible but all shows it',()=>{
  assert.deepEqual(searchPlaces(idx,'',{mode:'recommended'}).results.map(x=>x.id).sort(),['a','b','d']);
  assert.equal(searchPlaces(idx,'',{mode:'all'}).results.length,4);
});

test('quick and advanced filters combine and counts are dynamic',()=>{
  const out=searchPlaces(idx,'',{mode:'all',favorites:true,sources:['game'],surfaces:['asphalt']});
  assert.deepEqual(out.results.map(x=>x.id),['b']);
  const scenic=searchPlaces(idx,'',{mode:'all',categories:['scenic_roads'],surfaces:['asphalt']});
  assert.equal(scenic.counts.categories.scenic_roads,1);
  assert.deepEqual(activeFilterChips({categories:['scenic_roads'],surfaces:['asphalt'],favorites:true}).map(x=>x.key),['favorites','category:scenic_roads','surface:asphalt']);
});

test('sorting supports recommended name scenic and recent deterministically',()=>{
  assert.equal(searchPlaces(idx,'',{mode:'all',sort:'name'}).results[0].id,'b');
  assert.equal(searchPlaces(idx,'',{mode:'all',sort:'scenic'}).results[0].id,'a');
});

test('3000 place search remains bounded',()=>{
  const big=buildSearchIndex(Array.from({length:3000},(_,i)=>({...places[0],id:'p'+i,name:'Place '+i,aliases:['Mountain '+i]})));
  const start=performance.now(); const out=searchPlaces(big,'mountan 29',{mode:'all'}); const elapsed=performance.now()-start;
  assert.ok(out.results.length>0); assert.ok(elapsed<250,`search took ${elapsed} ms`);
});
