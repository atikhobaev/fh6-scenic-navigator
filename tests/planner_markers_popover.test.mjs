import test from 'node:test';
import assert from 'node:assert/strict';
import {clusterMarkers,markerVisualModel} from '../static/planner/map.js';
import {buildPlacePopoverModel,localPlaceImagePath} from '../static/planner/popover.js';

test('selected and route markers are never absorbed into clusters',()=>{
  const markers=[
    {id:'a',x:10,y:10,clusterable:true},
    {id:'b',x:11,y:11,clusterable:true},
    {id:'route',x:12,y:12,clusterable:false},
    {id:'selected',x:13,y:13,clusterable:false},
  ];
  const out=clusterMarkers(markers,50);
  assert.equal(out.filter(x=>x.type==='cluster').length,1);
  assert.equal(out.find(x=>x.id==='route')?.type,'marker');
  assert.equal(out.find(x=>x.id==='selected')?.type,'marker');
});

test('marker visual model uses layer icon and strict visual priority',()=>{
  const p={id:'x',source:'game',category:'barn_find',favorite:true};
  const normal=markerVisualModel(p,{});
  assert.equal(normal.layerId,'barn_finds');
  assert.equal(normal.icon,'barn');
  assert.equal(markerVisualModel(p,{favorite:true}).state,'favorite');
  assert.equal(markerVisualModel(p,{selected:true,favorite:true}).state,'selected');
  assert.equal(markerVisualModel(p,{route:true,selected:true,favorite:true}).state,'route');
});

test('popover only accepts local cached media paths',()=>{
  assert.equal(localPlaceImagePath({image_thumb:'/media/places/community/a.webp'}),'/media/places/community/a.webp');
  assert.equal(localPlaceImagePath({image:'https://example.test/a.jpg'}),null);
  assert.equal(localPlaceImagePath({image:'/static/other.jpg'}),null);
});

test('photo popover exposes route destination and favorite actions',()=>{
  const p={id:'x',name:'Hidden Viewpoint',source:'community',category:'scenic_spot',image:'/media/places/community/x.webp',favorite:false};
  const model=buildPlacePopoverModel(p,{inRoute:false});
  assert.equal(model.title,'Hidden Viewpoint');
  assert.equal(model.image,'/media/places/community/x.webp');
  assert.equal(model.compact,false);
  assert.deepEqual(model.actions.map(x=>x.id),['add','destination','favorite']);
});

test('place without photo gets compact text-only popover',()=>{
  const model=buildPlacePopoverModel({id:'x',name:'No Photo',source:'game',category:'landmark'});
  assert.equal(model.image,null);
  assert.equal(model.compact,true);
});

test('popover prefers full local image while search helper prefers thumbnail',()=>{
  const p={image:'/media/places/full.webp',image_thumb:'/media/places/thumb.webp'};
  assert.equal(localPlaceImagePath(p),'/media/places/full.webp');
  assert.equal(localPlaceImagePath(p,'thumb'),'/media/places/thumb.webp');
});

test('unroutable place disables route actions but keeps favorite available',()=>{
  const p={id:'x',name:'Remote Spot',source:'game',category:'landmark',navigation:{anchor_point_id:null}};
  const model=buildPlacePopoverModel(p,{inRoute:false});
  const add=model.actions.find(x=>x.id==='add');
  const destination=model.actions.find(x=>x.id==='destination');
  const favorite=model.actions.find(x=>x.id==='favorite');
  assert.equal(add.disabled,true);
  assert.equal(destination.disabled,true);
  assert.equal(favorite.disabled,false);
  assert.match(add.reason,/route|road|anchor/i);
});
