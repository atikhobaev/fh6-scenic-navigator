import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import zlib from 'node:zlib';
import {hubToPixel,pixelToWorld,buildDirectionalLoop} from '../static/nav_logic.js';
import {buildDirectedRuntime,routeBetweenWorldPoints} from '../static/directed_nav.js';

const payload=JSON.parse(zlib.gunzipSync(fs.readFileSync(new URL('../static/data/fh6_navgraph_v1.json.gz',import.meta.url))));
const seed=JSON.parse(fs.readFileSync(new URL('../static/route.json',import.meta.url),'utf8'));
const rt=buildDirectedRuntime(payload);

for (const direction of ['forward','reverse']) {
  test(`bundled WVAN graph connects every scenic leg in ${direction} direction`,()=>{
    const waypoints=buildDirectionalLoop(seed.waypoints,direction);
    const worlds=waypoints.map(w=>{
      const p=hubToPixel(w.lat,w.lng), q=pixelToWorld(p[0],p[1]);
      return {x:q[0],z:q[1]};
    });
    for(let i=0;i<worlds.length-1;i++){
      const route=routeBetweenWorldPoints(worlds[i],worlds[i+1],rt,{avoidDirt:true});
      assert.ok(route,`leg ${i} ${waypoints[i].game} -> ${waypoints[i+1].game}`);
      assert.ok(route.segmentIds.length>0);
    }
  });
}

test('bundled graph is the known route-validated Brio source',()=>{
  assert.equal(payload.source.sha256,'f06b4b958e60af5e52bc456173a5ba2b3ce6c900c732c8c5d96bd426498f5dbb');
  assert.equal(payload.capabilities.route_validated,true);
  assert.equal(payload.stats.points,38473);
  assert.equal(payload.stats.segments,71222);
});
