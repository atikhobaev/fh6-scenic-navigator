import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {SUPPORTED_LOCALES,hasTranslation,translateForLocale} from '../static/i18n.js';
import {localizedGameName,localizedPlaceName,setPlaceNamesMap} from '../static/place_locale.js';

const read=p=>fs.readFileSync(new URL(p,import.meta.url),'utf8');
const driveHtml=read('../static/index.html');
const plannerHtml=read('../static/planner/index.html');
const driveJs=read('../static/app.js');
const plannerJs=read('../static/planner/planner.js');
const i18nSrc=read('../static/i18n.js');

function keysIn(html){
  const out=new Set();
  for(const re of [/data-i18n="([^"]+)"/g,/data-i18n-placeholder="([^"]+)"/g,/data-i18n-title="([^"]+)"/g,/data-i18n-aria-label="([^"]+)"/g,/data-tooltip-key="([^"]+)"/g]) {
    for(const m of html.matchAll(re)) out.add(m[1]);
  }
  return [...out];
}

test('supported UI locales are exactly English Simplified Chinese Russian and Latin American Spanish',()=>{
  assert.deepEqual(SUPPORTED_LOCALES,['en-US','zh-CN','ru-RU','es-419']);
  assert.equal(translateForLocale('ru-RU','planner.startNavigation'),'НАЧАТЬ НАВИГАЦИЮ');
  assert.equal(translateForLocale('zh-CN','planner.startNavigation'),'开始导航');
  assert.match(translateForLocale('es-419','planner.startNavigation'),/INICIAR/i);
});

test('every static DRIVE and PLAN translation key exists in all four dictionaries',()=>{
  for(const key of [...new Set([...keysIn(driveHtml),...keysIn(plannerHtml)])]) {
    for(const locale of SUPPORTED_LOCALES) assert.equal(hasTranslation(locale,key),true,`${locale} missing ${key}`);
  }
});

test('localized POI names use selected official name then English fallback',()=>{
  setPlaceNamesMap({'game.a':{'en-US':'English Game Name','ru-RU':'Русское имя'}});
  const place={id:'game.a',name:'Canonical',game:'English Canonical'};
  assert.equal(localizedPlaceName(place,'ru-RU'),'Русское имя');
  assert.equal(localizedPlaceName(place,'zh-CN'),'English Game Name');
  assert.equal(localizedPlaceName({id:'missing',name:'English fallback'},'es-419'),'English fallback');
});

test('DRIVE can resolve a unique official localization from an English game name',()=>{
  setPlaceNamesMap({
    'game.a':{'en-US':'Hirosaki Castle','ru-RU':'Замок Хиросаки','zh-CN':'弘前城'},
    'game.b':{'en-US':'Mt. Haruna','es-419':'Monte Haruna'},
  });
  assert.equal(localizedGameName('Hirosaki Castle','ru-RU'),'Замок Хиросаки');
  assert.equal(localizedGameName('Hirosaki Castle','zh-CN'),'弘前城');
  assert.equal(localizedGameName('Mt. Haruna','ru-RU'),'Mt. Haruna');
  assert.equal(localizedGameName('Unknown Place','es-419'),'Unknown Place');
});

test('DRIVE and PLAN expose stable Horizon Command mode switch and v1.20.0 build label',()=>{
  for(const html of [driveHtml,plannerHtml]) {
    assert.match(html,/class="[^"]*hc-mode[^"]*"/);
    assert.match(html,/v1\.20\.0/);
    assert.match(html,/\/styles\/tailwind\.css/);
  }
  assert.match(driveHtml,/driveLocaleButton/);
  assert.doesNotMatch(driveHtml,/data-locale-select/);
  assert.doesNotMatch(plannerHtml,/data-locale-select|plannerLocaleSelect/);
  assert.match(driveHtml,/<strong[^>]*>DRIVE<\/strong>[\s\S]*href="\/planner\/"[^>]*>PLAN</);
  assert.match(plannerHtml,/href="\/"[^>]*>DRIVE<[\s\S]*<strong[^>]*>PLAN<\/strong>/);
});

test('PLAN runtime binds shared i18n and localized place-name rendering',()=>{
  assert.match(plannerJs,/from ['"]\.\.\/i18n\.js['"]/);
  assert.match(plannerJs,/from ['"]\.\.\/place_locale\.js['"]/);
  assert.doesNotMatch(plannerJs,/bindLocaleSelect/);
  assert.match(plannerJs,/loadPlaceNames/);
  assert.match(plannerJs,/localizedPlaceName/);
  assert.match(plannerJs,/fh6:localechange/);
});

test('DRIVE runtime binds shared i18n and localizes route waypoint names',()=>{
  assert.match(driveJs,/from ['"]\.\/i18n\.js['"]/);
  assert.match(driveJs,/from ['"]\.\/place_locale\.js['"]/);
  assert.match(driveJs,/bindLocaleFlagMenu/);
  assert.match(driveJs,/loadPlaceNames/);
  assert.match(driveJs,/localizedRouteItemName/);
  assert.match(driveJs,/fh6:localechange/);
});
test('launcher language can seed browser locale through lang query parameter',()=>{
  assert.match(i18nSrc,/URLSearchParams\(location\.search\)/);
  assert.match(i18nSrc,/params\.get\('lang'\)/);
});
