import {getLocale,translateForLocale} from './i18n.js';

const TARGET_SELECTOR='button, a.btn, a.hc-button, [role="button"]';
let installed=false;
let bubble=null;
let activeTarget=null;

export function tooltipTextForElement(el,locale=getLocale()){
  const tooltipKey=String(el?.dataset?.tooltipKey||'').trim();
  return tooltipKey?translateForLocale(locale,tooltipKey):'';
}

function prepareElement(el){
  if(el?.hasAttribute?.('title')){
    if(!el.dataset.tooltipSourceTitle)el.dataset.tooltipSourceTitle=el.getAttribute('title')||'';
    el.removeAttribute('title');
  }
  return el;
}
function prepare(root=document){
  root.querySelectorAll?.(TARGET_SELECTOR).forEach(prepareElement);
}

function ensureBubble(){
  if(bubble||typeof document==='undefined')return bubble;
  bubble=document.createElement('div');bubble.className='hc-tooltip-bubble';bubble.setAttribute('role','tooltip');bubble.hidden=true;document.body.append(bubble);return bubble;
}

function hide(){if(bubble)bubble.hidden=true;activeTarget=null}
function show(el){
  prepareElement(el);
  const text=tooltipTextForElement(el);if(!text)return hide();
  const tip=ensureBubble();if(!tip)return;
  activeTarget=el;tip.textContent=text;tip.hidden=false;
  const r=el.getBoundingClientRect(),pad=8,maxLeft=Math.max(pad,window.innerWidth-tip.offsetWidth-pad);
  const preferredLeft=r.left+r.width/2-tip.offsetWidth/2;
  tip.style.left=`${Math.min(maxLeft,Math.max(pad,preferredLeft))}px`;
  const above=r.top-tip.offsetHeight-9;
  tip.style.top=`${above>=pad?above:Math.min(window.innerHeight-tip.offsetHeight-pad,r.bottom+9)}px`;
}
function targetFrom(node){return node?.closest?.(TARGET_SELECTOR)||null}

export function installTooltips(root=document){
  prepare(root);if(installed)return;installed=true;ensureBubble();
  document.addEventListener('pointerover',e=>{const el=targetFrom(e.target);if(el)show(el)});
  document.addEventListener('pointerout',e=>{const el=targetFrom(e.target);if(el&&(!e.relatedTarget||!el.contains(e.relatedTarget)))hide()});
  document.addEventListener('focusin',e=>{const el=targetFrom(e.target);if(el)show(el)});
  document.addEventListener('focusout',e=>{if(targetFrom(e.target))hide()});
  document.addEventListener('keydown',e=>{if(e.key==='Escape')hide()});
  window.addEventListener('resize',hide,{passive:true});
  window.addEventListener('scroll',hide,true);
  window.addEventListener('fh6:localechange',()=>queueMicrotask(()=>{prepare(root);if(activeTarget)show(activeTarget)}));
}
