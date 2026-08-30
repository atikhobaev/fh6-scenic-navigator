import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {localizedRouteItemName, humanizeStablePlaceId} from '../static/place_locale.js';

const read = p => fs.readFileSync(new URL(`../${p}`, import.meta.url), 'utf8');

test('route target label resolves catalog place name and never leaks builtin stable id', () => {
  const places = new Map([['builtin.game.landmark.landmark_015', {
    id: 'builtin.game.landmark.landmark_015',
    name: 'Landmark #015',
    game: 'Landmark #015',
  }]]);
  const label = localizedRouteItemName({place_id:'builtin.game.landmark.landmark_015', place_name:'builtin.game.landmark.landmark_015'}, places, 'ru-RU', {});
  assert.equal(label, 'Landmark #015');
  assert.ok(!label.includes('builtin.game.'));
  assert.equal(humanizeStablePlaceId('builtin.game.landmark.landmark_015'), 'Landmark #015');
});

test('DRIVE uses compact flag language menu in left status block and toolbar has no locale select', () => {
  const html = read('static/index.html');
  assert.match(html, /id="driveLocaleButton"[^>]*class="[^"]*locale-flag-button/);
  assert.match(html, /id="driveLocaleMenu"/);
  assert.doesNotMatch(html, /id="driveLocaleSelect"/);
  const statusAt = html.indexOf('class="drive-status');
  const languageAt = html.indexOf('id="driveLocaleButton"');
  const toolsAt = html.indexOf('class="drive-tools"');
  assert.ok(statusAt >= 0 && languageAt > statusAt && languageAt < toolsAt);
});

test('PLAN removes the standalone language selector', () => {
  const html = read('static/planner/index.html');
  assert.doesNotMatch(html, /plannerLocaleSelect|data-locale-select/);
});

test('text toolbar buttons are content-adaptive instead of fixed width', () => {
  const css = read('static/styles/app.css');
  assert.doesNotMatch(css, /\.drive-tool-wide\s*\{[^}]*width:\s*88px/);
  assert.doesNotMatch(css, /\.drive-tool-auto\s*\{[^}]*width:\s*105px/);
  assert.doesNotMatch(css, /\.drive-tool-record\s*\{[^}]*width:\s*72px/);
  assert.match(css, /\.drive-tool-wide[^}]*width:\s*auto/);
  assert.match(css, /\.drive-tools[^}]*min-width:\s*0/);
});

test('shared tooltip runtime is loaded by DRIVE and PLAN and only renders authored help copy', () => {
  const drive = read('static/app.js');
  const planner = read('static/planner/planner.js');
  const tooltip = read('static/tooltips.js');
  assert.match(drive, /installTooltips/);
  assert.match(planner, /installTooltips/);
  assert.match(tooltip, /TARGET_SELECTOR=['"]button,/);
  assert.match(tooltip, /querySelectorAll\?\.\(TARGET_SELECTOR\)/);
  assert.match(tooltip, /data-tooltip-key|tooltipKey/);
  assert.doesNotMatch(tooltip, /common\.tooltipFallback/);
  assert.match(tooltip, /fh6:localechange/);
});
