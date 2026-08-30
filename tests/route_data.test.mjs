import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {hubToPixel, buildDirectionalLoop} from '../static/nav_logic.js';

const route = JSON.parse(fs.readFileSync(new URL('../static/route.json', import.meta.url), 'utf8'));
const MAP_MIN = 8128 * 256;
const MAP_MAX = 8192 * 256;

const games = route.waypoints.map(w => w.game);

test('scenic route is configured as a loop and closes at Hirosaki in both directions', () => {
  assert.equal(route.loop, true);
  const forward = buildDirectionalLoop(route.waypoints, 'forward');
  const reverse = buildDirectionalLoop(route.waypoints, 'reverse');
  assert.equal(forward[0].game, 'Hirosaki Castle');
  assert.equal(forward.at(-1).game, 'Hirosaki Castle');
  assert.equal(reverse[0].game, 'Hirosaki Castle');
  assert.equal(reverse.at(-1).game, 'Hirosaki Castle');
  assert.equal(reverse[1].game, route.waypoints.at(-1).game);
});

test('removed dead-end or unwanted POIs are not in v1.5 itinerary', () => {
  for (const removed of ['Lake Nukabira', 'Snow Monster Forest', 'Hotel Thunderbird']) {
    assert.equal(games.includes(removed), false, `${removed} should be removed`);
  }
});

test('Narai-Juku and Yoshinoyama are both retained in the full-map return leg', () => {
  assert.ok(games.includes('Narai-Juku'));
  assert.ok(games.includes('Yoshinoyama'));
});

test('scenic roadside POIs request through-asphalt snapping', () => {
  for (const game of ['Sotoyama Ski Resort', 'Shirakawa-go', 'Bandai Azuma Skyline', 'Mt. Haruna', 'Ine', 'Seabed Road']) {
    const wp = route.waypoints.find(w => w.game === game);
    assert.ok(wp, `${game} missing`);
    assert.equal(wp.snapMode, 'throughAsphalt');
  }
});

test('all landmark coordinates project inside the FH6 map tile extent', () => {
  for (const waypoint of route.waypoints) {
    const [x, y] = hubToPixel(waypoint.lat, waypoint.lng);
    assert.ok(x >= MAP_MIN && x < MAP_MAX, `${waypoint.game}: x=${x}`);
    assert.ok(y >= MAP_MIN && y < MAP_MAX, `${waypoint.game}: y=${y}`);
  }
});


test('expanded scenic route deliberately uses the eastern third of the map', () => {
  const eastern = ['Mt. Haruna','Wind Farm','Ine','Arashiyama Bamboo Forest','Satta Pass','Seabed Road','Meoto Iwa Rock','Seaside Park'];
  for (const game of eastern) assert.ok(games.includes(game), `${game} should be in the expanded eastern loop`);
  const farEastCount = route.waypoints.filter(w => w.lng > -0.56).length;
  assert.ok(farEastCount >= 6, `expected at least 6 far-east POIs, got ${farEastCount}`);
});

test('seed itinerary forms an eastern descent and a western return instead of jumping back and forth', () => {
  const idx = name => games.indexOf(name);
  assert.ok(idx('Mt. Haruna') < idx('Ine'));
  assert.ok(idx('Ine') < idx('Satta Pass'));
  assert.ok(idx('Satta Pass') < idx('Seaside Park'));
  assert.ok(idx('Seaside Park') < idx('Daikoku Parking Area'));
  assert.ok(idx('Shibuya Crossing') < idx('Hakone Nanamagari'));
  assert.ok(idx('Fuji Shibazakura') < idx('Narai-Juku'));
  assert.ok(idx('Narai-Juku') < idx('Tateyama Kurobe Alpine Route'));
});
