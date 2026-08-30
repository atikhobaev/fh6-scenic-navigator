const NS='http://www.w3.org/2000/svg';
const common={fill:'none',stroke:'currentColor','stroke-width':'1.6','stroke-linecap':'round','stroke-linejoin':'round'};
const shape=(tag,attrs)=>({tag,attrs:{...common,...attrs}});

export const ICONS={
  home:{shapes:[shape('path',{d:'M2.5 7.4 8 3l5.5 4.4V14H9.7v-4H6.3v4H2.5Z'})]},
  landmark:{shapes:[shape('path',{d:'M8 14s4-4.4 4-7A4 4 0 1 0 4 7c0 2.6 4 7 4 7Z'}),shape('circle',{cx:8,cy:7,r:1.35})]},
  mountain:{shapes:[shape('path',{d:'M1.8 13.5 6.1 6l2.2 3.4L10.1 6l4.1 7.5Z'}),shape('path',{d:'m4.8 8.3 1.3-2.3 1.4 2.1'})]},
  road:{shapes:[shape('path',{d:'M5.1 14c4-3.1-1.5-5 3.8-8.3C10.8 4.5 11 3.3 10.8 2'}),shape('path',{d:'M9 14c3.8-3.2-1.6-4.8 3.2-8.1'})]},
  camera:{shapes:[shape('rect',{x:2.2,y:5.1,width:11.6,height:7.7,rx:1.4}),shape('path',{d:'m5 5.1 1-2h4l1 2'}),shape('circle',{cx:8,cy:8.9,r:2.2})]},
  festival:{shapes:[shape('path',{d:'M3 14V2.5'}),shape('path',{d:'M3.2 3h8.2l-1.8 2.3 1.8 2.3H3.2'})]},
  egg:{shapes:[shape('path',{d:'M8 2.2c2.4 0 4.2 4.2 4.2 7.2A4.2 4.2 0 0 1 3.8 9.4C3.8 6.4 5.6 2.2 8 2.2Z'})]},
  pin:{shapes:[shape('circle',{cx:8,cy:8,r:3.2}),shape('circle',{cx:8,cy:8,r:.8,fill:'currentColor',stroke:'none'})]},
  book:{shapes:[shape('path',{d:'M2.5 3.2h4.1c1 0 1.4.5 1.4 1.3v8.3c0-.9-.5-1.4-1.5-1.4h-4Z'}),shape('path',{d:'M13.5 3.2H9.4C8.4 3.2 8 3.7 8 4.5v8.3c0-.9.5-1.4 1.5-1.4h4Z'})]},
  car:{shapes:[shape('path',{d:'m3.1 9 1.2-3.2h7.4L12.9 9l1.1 1v2.2H2V10Z'}),shape('circle',{cx:4.2,cy:12.2,r:.9}),shape('circle',{cx:11.8,cy:12.2,r:.9})]},
  magazine:{shapes:[shape('rect',{x:2.7,y:2.5,width:10.6,height:11,rx:1}),shape('path',{d:'M5 5h6M5 7.5h6M5 10h3.7'})]},
  drift:{shapes:[shape('path',{d:'M2.4 11.5c2.4-5.2 5.2-6.4 9.5-4.7'}),shape('path',{d:'m9.9 4.3 2.8 2.7-3.5 1.4'}),shape('path',{d:'M4.2 13.2h6.2'})]},
  briefcase:{shapes:[shape('rect',{x:2.2,y:5.1,width:11.6,height:8,rx:1.2}),shape('path',{d:'M5.7 5.1V3.3h4.6v1.8M2.5 8.5h11'})]},
  star:{shapes:[shape('path',{d:'m8 2.1 1.7 3.5 3.9.6-2.8 2.7.7 3.9L8 11l-3.5 1.8.7-3.9-2.8-2.7 3.9-.6Z'})]},
  speedometer:{shapes:[shape('path',{d:'M2.4 11.8a6 6 0 1 1 11.2 0'}),shape('path',{d:'m8 9.8 3-3'}),shape('circle',{cx:8,cy:10,r:.8})]},
  speed_zone:{shapes:[shape('path',{d:'M2.2 12.5h11.6M4 10l1.2-4h5.6L12 10'}),shape('path',{d:'M6.2 7.8h3.6'})]},
  warning:{shapes:[shape('path',{d:'M8 2.2 14 13H2Z'}),shape('path',{d:'M8 5.7v3.5'}),shape('circle',{cx:8,cy:11.1,r:.55,fill:'currentColor',stroke:'none'})]},
  trailblazer:{shapes:[shape('path',{d:'M3 14V2.3'}),shape('path',{d:'M3 3h8.5l-2 2.3 2 2.2H3'}),shape('path',{d:'m7 10 2 2 3-3'})]},
  car_group:{shapes:[shape('path',{d:'m1.8 9.2 1-2.5h5.4l1 2.5.8.8v1.7H1v-1.7Z'}),shape('path',{d:'m7.8 6.1.8-2h4.5l.9 2.4'}),shape('circle',{cx:3.1,cy:11.7,r:.7}),shape('circle',{cx:7.9,cy:11.7,r:.7})]},
  drag:{shapes:[shape('path',{d:'M3 3v10M13 3v10'}),shape('path',{d:'M5 5h6M5 8h6M5 11h6'})]},
  stopwatch:{shapes:[shape('circle',{cx:8,cy:9,r:4.6}),shape('path',{d:'M8 1.8v2M6.2 1.8h3.6M11.4 4.7l1.3-1.3M8 9l2-1.7'})]},
  spark:{shapes:[shape('path',{d:'m8 1.8 1.2 4 4-1.2-2.7 3.2 2.7 3.2-4-1.2-1.2 4-1.2-4-4 1.2 2.7-3.2-2.7-3.2 4 1.2Z'})]},
  race_flag:{shapes:[shape('path',{d:'M3 14V2.5'}),shape('path',{d:'M3 3h8.6v5H3'}),shape('path',{d:'M5.2 3v5M7.4 3v5M9.6 3v5M3 5.5h8.6'})]},
  race_mountain:{shapes:[shape('path',{d:'M2 12.7 5.3 7 7 9.5 9 5.8l4.6 6.9Z'}),shape('path',{d:'M11.2 2.5v4M11.2 2.8h3l-.8 1 .8 1h-3'})]},
  rally:{shapes:[shape('path',{d:'M2.4 12.5 5 5.5h6l2.6 7'}),shape('path',{d:'M5.8 8.2h4.4'}),shape('path',{d:'M8 2.2v2'})]},
  cross_country:{shapes:[shape('path',{d:'M2.5 13 5 7.5 7.1 10l2.4-5 4 8'}),shape('path',{d:'M3 3l10 10M13 3 3 13'})]},
  barn:{shapes:[shape('path',{d:'M2.2 7.1 8 2.8l5.8 4.3V14H2.2Z'}),shape('path',{d:'M5.1 14V8.4h5.8V14M5.1 8.4l5.8 5.6M10.9 8.4 5.1 14'})]},
  treasure:{shapes:[shape('path',{d:'M2.7 6.1 5.2 3h5.6l2.5 3.1L8 13.5Z'}),shape('path',{d:'M2.7 6.1h10.6M5.2 3 8 13.5 10.8 3'})]},
  board:{shapes:[shape('rect',{x:3,y:2.5,width:10,height:9,rx:.8}),shape('path',{d:'M5 5h6M5 7.5h4M6 11.5v2M10 11.5v2'})]},
  collectible:{shapes:[shape('circle',{cx:8,cy:8,r:5}),shape('path',{d:'m8 4.2 1.1 2.2 2.5.4-1.8 1.8.4 2.5L8 9.9l-2.2 1.2.4-2.5-1.8-1.8 2.5-.4Z'})]},
  mascot:{shapes:[shape('circle',{cx:8,cy:8,r:5}),shape('circle',{cx:6.2,cy:7,r:.7,fill:'currentColor',stroke:'none'}),shape('circle',{cx:9.8,cy:7,r:.7,fill:'currentColor',stroke:'none'}),shape('path',{d:'M5.7 9.4c1.2 1.2 3.4 1.2 4.6 0'})]},
  jump:{shapes:[shape('path',{d:'M2 12.5h4.3l2.6-5.8H14'}),shape('path',{d:'m10.5 3 3.5 3.7-3.7 3.2'})]},
};

export function iconSpec(id){return ICONS[id]||ICONS.pin;}

function attrsToString(attrs){return Object.entries(attrs).map(([k,v])=>`${k}="${String(v).replaceAll('&','&amp;').replaceAll('"','&quot;')}"`).join(' ');}
export function iconMarkup(id,className='svg-icon'){
  const spec=iconSpec(id);
  const body=spec.shapes.map(s=>`<${s.tag} ${attrsToString(s.attrs)}/>`).join('');
  return `<svg class="${className}" viewBox="0 0 16 16" aria-hidden="true" focusable="false">${body}</svg>`;
}

export function createIconElement(id,{className='svg-icon',size=16,x=null,y=null}={}){
  const node=document.createElementNS(NS,'svg');
  node.setAttribute('viewBox','0 0 16 16');
  node.setAttribute('aria-hidden','true');
  node.setAttribute('focusable','false');
  if(className)node.setAttribute('class',className);
  if(size!=null){node.setAttribute('width',String(size));node.setAttribute('height',String(size));}
  if(x!=null)node.setAttribute('x',String(x));
  if(y!=null)node.setAttribute('y',String(y));
  for(const spec of iconSpec(id).shapes){
    const child=document.createElementNS(NS,spec.tag);
    for(const[k,v]of Object.entries(spec.attrs))child.setAttribute(k,String(v));
    node.append(child);
  }
  return node;
}
