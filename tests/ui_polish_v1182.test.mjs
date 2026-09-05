import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {tooltipTextForElement} from '../static/tooltips.js';

const read = p => fs.readFileSync(new URL(`../${p}`, import.meta.url), 'utf8');

function fakeButton({tooltipKey='', i18nTitle='', i18n='', aria='', text=''}={}){
  return {
    dataset:{tooltipKey, i18nTitle, i18n},
    textContent:text,
    getAttribute(name){return name==='aria-label'?aria:'';},
  };
}

test('tooltip runtime shows only authored help copy and never generic action fallback', () => {
  assert.equal(tooltipTextForElement(fakeButton({tooltipKey:'drive.zoomInHelp'}),'ru-RU'), 'Приблизить карту, чтобы подробнее видеть дорогу и развязки.');
  assert.equal(tooltipTextForElement(fakeButton({i18nTitle:'drive.zoomIn', text:'＋'}),'ru-RU'), '');
  assert.equal(tooltipTextForElement(fakeButton({text:'↑'}),'ru-RU'), '');
  const source=read('static/tooltips.js');
  assert.doesNotMatch(source,/common\.tooltipFallback/);
});

test('language chooser uses bundled SVG flag assets instead of Unicode emoji flags', () => {
  const html=read('static/index.html');
  const i18n=read('static/i18n.js');
  for(const locale of ['en-US','zh-CN','ru-RU','es-419']){
    assert.match(i18n,new RegExp(`assets/flags/${locale}\\.svg`));
    assert.ok(fs.existsSync(new URL(`../static/assets/flags/${locale}.svg`, import.meta.url)), `${locale} flag asset missing`);
  }
  assert.doesNotMatch(html,/🇬🇧|🇨🇳|🇷🇺|🇲🇽|🌐/u);
  assert.match(html,/class="locale-flag-image"/);
});

test('language menu has an explicit official POI localization status row', () => {
  const html=read('static/index.html');
  const i18n=read('static/i18n.js');
  assert.match(html,/id="localePoiStatus"/);
  assert.match(i18n,/poiLocalizationStatus/);
  assert.match(i18n,/place_names_meta\.json/);
});

test('SVG flag button treats clicks on its child image as clicks inside the language control', () => {
  const source=read('static/i18n.js');
  assert.match(source,/!button\.contains\(e\.target\)/);
  assert.doesNotMatch(source,/e\.target!==button/);
});

test('server API version matches the visible v1.20.0 build label', () => {
  const server=read('server.py');
  assert.match(server,/APP_VERSION\s*=\s*['"]1\.20\.0['"]/);
});
