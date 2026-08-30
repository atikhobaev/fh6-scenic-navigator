import {api} from './api.js';
import {createLibraryState,updatePlaces,reduceLibrary} from './library.js';
import {searchPlaces} from './search.js';
import {PlannerMap} from './map.js';
import {
  LAYER_GROUPS,LAYER_REGISTRY,normalizeLayerState,serializeLayerState,applyLayerPreset,setAllGroupsCollapsed,
  toggleLayer,toggleGroup,layerForPlace,isPlaceVisible,layerCounts
} from './layers.js';
import {buildPlacePopoverModel,localPlaceImagePath,isPlaceRoutable} from './popover.js';
import {createIconElement} from './icons.js';
import {canStartNavigation,shouldAcceptPreview,routeItemLabel,expandedItemModel} from './route_editor.js';
import {applyTranslations,getLocale,t} from '../i18n.js';
import {loadPlaceNames,localizedPlaceName} from '../place_locale.js';
import {installTooltips} from '../tooltips.js';

const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const LAYER_STORAGE='fh6PlannerLayersV1';
const FILTER_STORAGE='fh6PlannerMapFiltersV1';
const QUICK_STORAGE='fh6PlannerQuickFiltersV1';
const defaultFacets={surfaces:['asphalt','dirt','mixed','unknown'],sources:['game','curated','community','user']};

function readJsonStorage(key,fallback){try{return JSON.parse(localStorage.getItem(key)||'null')??fallback}catch{return fallback}}
function saveJsonStorage(key,value){try{localStorage.setItem(key,JSON.stringify(value))}catch{}}
function km(m){return m==null?'—':`${(m/1000).toFixed(m<10000?1:0)} km`}
function clamp(n,min,max){return Math.max(min,Math.min(max,n))}
function placeDisplayName(place){return localizedPlaceName(place,getLocale())}
function localizedPlace(place){return place?{...place,name:placeDisplayName(place),aliases:[...new Set([...(place.aliases||[]),place.name,place.game].filter(Boolean))]}:place}
function localizedPlaceMap(){return new Map(state.places.map(p=>[p.id,localizedPlace(p)]))}
function layerDisplayLabel(def){return def?.labelKey?t(def.labelKey):def?.label||''}
function sourceDisplayLabel(source){return ({game:t('common.officialGame'),curated:t('common.curated'),community:t('common.community'),user:t('common.myPlaces')})[source]||String(source||'')}
function routeDisplayLabel(item){return routeItemLabel(item,localizedPlaceMap())}
function rebuildLocalizedLibrary(){
  state.library=updatePlaces(state.library,state.places.map(localizedPlace));
  state.library={...state.library,filters:{...state.library.filters,mode:'all'}};
}
function routeStopLabel(item){
  if(item?.type==='scenic_road'||item?.type==='scenic_loop')return t('planner.scenicBlock');
  if(item?.stop_type==='via')return t('planner.via');
  return t('planner.stop');
}

const storedFacets=readJsonStorage(FILTER_STORAGE,defaultFacets);
const storedQuick=readJsonStorage(QUICK_STORAGE,{favorites:false,scenic:false,photos:false,inRoute:false});
const state={
  places:[],placeMap:new Map(),library:createLibraryState([],{filters:{mode:'all',sort:'recommended'}}),
  route:null,preview:null,selectedPlaceId:null,expandedItemId:null,searchRevealId:null,searchQuery:'',
  layerState:normalizeLayerState(readJsonStorage(LAYER_STORAGE,{})),
  facets:{surfaces:new Set(storedFacets.surfaces||defaultFacets.surfaces),sources:new Set(storedFacets.sources||defaultFacets.sources)},
  quick:{favorites:Boolean(storedQuick.favorites),scenic:Boolean(storedQuick.scenic),photos:Boolean(storedQuick.photos),inRoute:Boolean(storedQuick.inRoute)},
  previewBusy:false,routePreviewSeq:0,dragItemId:null,addPlaceMode:null,
};
let toastTimer=null,renameTimer=null,searchTimer=null,diagnosticsGraph=null;

function toast(message,undo=null){
  const el=$('#toast'); if(!el)return; el.replaceChildren(document.createTextNode(message));
  if(undo){const b=document.createElement('button');b.textContent=` ${t('planner.undoAction')}`;b.className='ghost-btn';b.onclick=undo;el.append(b)}
  el.classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.classList.remove('show'),4200);
}
function saveIndicator(text=t('planner.autosavedStatus'),busy=false){const e=$('#saveStatus');if(!e)return;e.textContent=text;e.style.color=busy?'#ffd166':'#5bd49b'}
function routePlaceIds(){return new Set((state.route?.items||[]).map(i=>i.place_id).filter(Boolean))}
function persistLayers(){saveJsonStorage(LAYER_STORAGE,serializeLayerState(state.layerState))}
function persistFilters(){saveJsonStorage(FILTER_STORAGE,{surfaces:[...state.facets.surfaces],sources:[...state.facets.sources]});saveJsonStorage(QUICK_STORAGE,state.quick)}

function passesFacetAndQuick(place,{ignoreQuick=false}={}){
  const routeIds=routePlaceIds();
  if(routeIds.has(place.id)||place.id===state.selectedPlaceId||place.id===state.searchRevealId)return true;
  if(state.facets.sources.size&&!state.facets.sources.has(place.source))return false;
  if(state.facets.surfaces.size&&!state.facets.surfaces.has(place.surface||'unknown'))return false;
  if(ignoreQuick)return true;
  if(state.quick.favorites&&!place.favorite)return false;
  const layer=layerForPlace(place);
  if(state.quick.scenic&&!['scenic_spots','scenic_roads','community_scenic'].includes(layer.id))return false;
  if(state.quick.photos&&!localPlaceImagePath(place))return false;
  if(state.quick.inRoute&&!routeIds.has(place.id))return false;
  return true;
}
function visibleMapPlaces(){
  const routeIds=routePlaceIds();
  const context={routePlaceIds:routeIds,selectedId:state.selectedPlaceId,searchRevealId:state.searchRevealId};
  return state.places.filter(p=>passesFacetAndQuick(p)&&isPlaceVisible(p,state.layerState,context));
}
function searchOutput(){
  if(!state.searchQuery.trim())return {results:[],total:0};
  const all=searchPlaces(state.library.index,state.searchQuery,{mode:'all',sort:'recommended'}).results;
  const filtered=all.filter(p=>passesFacetAndQuick(p));
  return {results:filtered,total:filtered.length};
}

let map=null;
function makeMap(){
  map=new PlannerMap($('#plannerMap'),{
    onSelect:(obj,pos)=>{
      if(state.addPlaceMode==='pick'&&!obj){state.addPlaceMode=null;$('#mapHint').textContent=t('planner.mapHint');createPlaceAt(pos);return}
      if(obj?.id)selectPlace(obj.id,{center:false});
      else if(obj?.routeItem){state.expandedItemId=obj.routeItem.id;renderRoute()}
      else closePopover();
    },
    onWaypoint:w=>addTemporary(w,'stop'),onQuickAdd:w=>addTemporary(w,'stop'),onContext:()=>{},onRender:()=>positionPopover()
  });
}

async function loadAll(){
  saveIndicator(t('common.loading'),true);
  const [pd,route]=await Promise.all([api.places('all'),api.activeRoute()]);
  state.places=pd.places||[];state.placeMap=new Map(state.places.map(p=>[p.id,p]));rebuildLocalizedLibrary();
  state.route=route;$('#routeNameInput').value=route.name;await refreshPreview();renderAll();saveIndicator();
}
async function reloadPlaces(){
  const pd=await api.places('all');state.places=pd.places||[];state.placeMap=new Map(state.places.map(p=>[p.id,p]));rebuildLocalizedLibrary();renderFilters();renderSearch();renderMap();renderPopover();
}
async function reloadRoute(){
  state.route=await api.activeRoute();$('#routeNameInput').value=state.route.name;await refreshPreview();renderRoute();renderFilters();renderSearch();renderMap();renderPopover();
}
async function refreshPreview(){
  if(!state.route)return;const seq=++state.routePreviewSeq,rev=state.route.revision;state.previewBusy=true;$('#routeCalcStatus').textContent=t('planner.calculating');
  try{const p=await api.preview(state.route.id,rev);if(seq!==state.routePreviewSeq||!shouldAcceptPreview(state.route.revision,p.revision))return;state.preview=p}
  catch(e){state.preview={revision:rev,resolved:false,legs:[],geometry:[],total_distance_m:0,error:e.message}}
  finally{if(seq===state.routePreviewSeq){state.previewBusy=false;renderRoute();renderMap()}}
}
function renderAll(){renderFilters();renderSearch();renderRoute();renderMap();renderPopover()}
function renderMap(){if(!map)return;map.setData({places:visibleMapPlaces().map(localizedPlace),routeItems:state.route?.items||[],preview:state.preview,selected:state.selectedPlaceId})}

function renderFilters(){
  const base=state.searchQuery.trim()?searchOutput().results:state.places.filter(p=>passesFacetAndQuick(p,{ignoreQuick:false}));
  const counts=layerCounts(base,state.layerState);const visible=visibleMapPlaces();
  $('#mapPlaceCount').textContent=t('planner.visibleCount',{count:visible.length});$('#catalogPlaceCount').textContent=t('planner.totalCount',{count:state.places.length});
  for(const [id,key] of [['favoritesFilter','favorites'],['scenicFilter','scenic'],['photosFilter','photos'],['inRouteFilter','inRoute']])$('#'+id)?.classList.toggle('active',Boolean(state.quick[key]));
  const box=$('#layerGroups');box.replaceChildren();
  for(const group of LAYER_GROUPS){
    const wrap=document.createElement('section');wrap.className='layer-group'+(state.layerState.collapsed.has(group.id)?' collapsed':'');wrap.dataset.groupId=group.id;
    const head=document.createElement('button');head.className='layer-group-head';const groupOn=group.layers.every(id=>state.layerState.enabled.has(id));const groupCount=group.layers.reduce((n,id)=>n+(counts[id]||0),0);
    head.innerHTML=`<span class="layer-group-chevron">${state.layerState.collapsed.has(group.id)?'›':'⌄'}</span><span class="layer-group-title"></span><span class="layer-group-count">${groupCount}</span><span class="layer-group-toggle${groupOn?' on':''}"></span>`;
    head.querySelector('.layer-group-title').textContent=t(group.labelKey);
    head.onclick=e=>{if(e.target.closest('.layer-group-toggle')){state.layerState=toggleGroup(state.layerState,group.id);persistLayers()}else{state.layerState=normalizeLayerState(state.layerState);state.layerState.collapsed.has(group.id)?state.layerState.collapsed.delete(group.id):state.layerState.collapsed.add(group.id);persistLayers()}renderFilters();renderMap()};
    wrap.append(head);
    const items=document.createElement('div');items.className='layer-items';
    for(const id of group.layers){const def=LAYER_REGISTRY[id],row=document.createElement('div'),label=layerDisplayLabel(def);row.className='layer-row';row.innerHTML=`<span class="layer-icon"></span><span class="layer-label"></span><span class="layer-count">${counts[id]||0}</span><button class="layer-switch${state.layerState.enabled.has(id)?' on':''}"></button>`;row.querySelector('.layer-icon').append(createIconElement(def.icon,{className:'layer-svg-icon',size:14}));row.querySelector('.layer-label').textContent=label;row.querySelector('.layer-switch').setAttribute('aria-label',t('planner.layersToggle',{name:label}));row.onclick=()=>{state.layerState=toggleLayer(state.layerState,id);persistLayers();renderFilters();renderMap()};items.append(row)}
    wrap.append(items);box.append(wrap);
  }
}

function renderSearch(){
  const box=$('#searchResults'),q=state.searchQuery.trim();if(!q){box.classList.add('hidden');box.replaceChildren();state.searchRevealId=null;return}
  const out=searchOutput();box.classList.remove('hidden');box.replaceChildren();
  if(!out.results.length){const empty=document.createElement('div');empty.className='search-empty';empty.textContent=t('planner.noMatches');box.append(empty);return}
  for(const p of out.results.slice(0,30)){
    const row=document.createElement('div');row.className='search-result'+(p.id===state.selectedPlaceId?' active':'');row.dataset.id=p.id;const layer=layerForPlace(p);
    const icon=document.createElement('span');icon.className='search-result-icon';icon.append(createIconElement(layer.icon,{className:'search-svg-icon',size:18}));const text=document.createElement('div');const title=document.createElement('div');title.className='search-result-title';title.textContent=placeDisplayName(p);const meta=document.createElement('div');meta.className='search-result-meta';meta.textContent=`${layerDisplayLabel(layer)} · ${sourceDisplayLabel(p.source)}`;text.append(title,meta);row.append(icon,text);
    const image=localPlaceImagePath(p,'thumb');if(image){const img=document.createElement('img');img.className='search-result-thumb';img.src=image;img.alt='';img.loading='lazy';img.decoding='async';img.draggable=false;img.onerror=()=>img.remove();row.append(img)}else{const add=document.createElement('button');add.className='place-add';add.textContent='＋';add.title=isPlaceRoutable(p)?t('planner.addToRoute'):t('planner.noRoadAnchor');add.disabled=!isPlaceRoutable(p);add.onclick=e=>{e.stopPropagation();addPlaceToRoute(p)};row.append(add)}
    row.onclick=()=>{state.searchRevealId=p.id;selectPlace(p.id,{center:true});renderSearch()};box.append(row);
  }
  if(out.total>30){const more=document.createElement('div');more.className='search-empty';more.textContent=t('planner.moreResults',{count:out.total-30});box.append(more)}
}

function selectPlace(id,{center=true}={}){const p=state.placeMap.get(id);if(!p)return;state.selectedPlaceId=id;state.searchRevealId=id;if(center&&p.position)map.fitWorldPoints([p.position]);renderFilters();renderMap();renderPopover();renderSearch()}
function closePopover(){state.selectedPlaceId=null;state.searchRevealId=state.searchQuery.trim()?state.searchRevealId:null;renderMap();renderPopover();renderSearch()}
function positionPopover(){
  const box=$('#placePopover'),p=state.placeMap.get(state.selectedPlaceId);if(!box||box.classList.contains('hidden')||!p?.position||!map)return;
  const [sx,sy]=map.worldToScreen(p.position.x,p.position.z),w=box.offsetWidth||310,h=box.offsetHeight||220,root=map.root;
  const left=clamp(sx+16,8,Math.max(8,root.clientWidth-w-8));const top=clamp(sy-h/2,8,Math.max(8,root.clientHeight-h-8));box.style.left=`${left}px`;box.style.top=`${top}px`;
}
function renderPopover(){
  const box=$('#placePopover'),p=state.placeMap.get(state.selectedPlaceId);if(!p){box.classList.add('hidden');box.replaceChildren();return}
  const inRoute=routePlaceIds().has(p.id),uiPlace=localizedPlace(p),model=buildPlacePopoverModel(uiPlace,{inRoute}),layer=layerForPlace(p);box.className='place-popover'+(model.compact?' compact':'');box.replaceChildren();
  if(model.image){const img=document.createElement('img');img.className='place-popover-image';img.src=model.image;img.alt=placeDisplayName(p);img.loading='lazy';img.decoding='async';img.draggable=false;img.onerror=()=>{img.remove();box.classList.add('compact')};box.append(img)}
  const body=document.createElement('div');body.className='place-popover-body';const head=document.createElement('div');head.className='place-popover-head';const copy=document.createElement('div'),title=document.createElement('div'),sub=document.createElement('div');title.className='place-popover-title';title.textContent=placeDisplayName(p);sub.className='place-popover-sub';sub.textContent=`${layerDisplayLabel(layer)} · ${sourceDisplayLabel(p.source)}`;copy.append(title,sub);const close=document.createElement('button');close.className='place-popover-close';close.textContent='×';close.onclick=closePopover;head.append(copy,close);body.append(head);
  const actionLabels={add:t('planner.addToRoute'),destination:t('planner.setDestinationAction'),favorite:p.favorite?t('common.unfavorite'):t('common.favorite'),edit:t('planner.editAction'),delete:t('planner.deleteAction')};const actions=document.createElement('div');actions.className='place-popover-actions';for(const a of model.actions){const b=document.createElement('button');b.textContent=actionLabels[a.id]||a.label;b.dataset.action=a.id;if(a.id==='add'||a.id==='destination')b.className='primary';if(a.id==='delete')b.classList.add('danger');b.disabled=Boolean(a.disabled);if(a.reason)b.title=t('planner.noRoadAnchor');b.onclick=()=>popoverAction(p,a.id);actions.append(b)}body.append(actions);box.append(body);box.classList.remove('hidden');requestAnimationFrame(positionPopover);
}
async function popoverAction(place,action){
  try{
    if(action==='add')await addPlaceToRoute(place);
    else if(action==='destination')await setPlaceDestination(place);
    else if(action==='favorite'){await api.favorite(place.id,!place.favorite);await reloadPlaces()}
    else if(action==='edit'&&place.source==='user'){const name=prompt(t('planner.placeName'),placeDisplayName(place));if(name?.trim()){await api.updateUserPlace(place.id,{name:name.trim()});await reloadPlaces();selectPlace(place.id,{center:false})}}
    else if(action==='delete'&&place.source==='user'){if(confirm(t('planner.deleteConfirm',{name:placeDisplayName(place)}))){await api.deleteUserPlace(place.id,false);closePopover();await reloadPlaces()}}
  }catch(e){toast(e.message)}
}

function routeLeg(item){const idx=(state.route?.items||[]).findIndex(x=>x.id===item.id);return (state.preview?.legs||[])[idx]||{}}
function renderRoute(){
  if(!state.route)return;const items=state.route.items||[],box=$('#routeItems');box.replaceChildren();$('#routeNameInput').value=state.route.name;$('#routeNameInput').disabled=Boolean(state.route.read_only);$('#routeReadOnly').classList.toggle('hidden',!state.route.read_only);$('#emptyRoute').classList.toggle('hidden',items.length>0);
  items.forEach((item,i)=>{
    const card=document.createElement('article');card.className='route-item'+(item.id===state.expandedItemId?' expanded':'');card.draggable=true;card.dataset.itemId=item.id;
    const row=document.createElement('div');row.className='route-row';const drag=document.createElement('span');drag.className='drag-handle';drag.textContent='⋮⋮';const text=document.createElement('div');const title=document.createElement('div');title.className='route-title';title.textContent=`${i+1}. ${routeDisplayLabel(item)}`;const sub=document.createElement('div');sub.className='route-sub';const leg=routeLeg(item);sub.textContent=`${routeStopLabel(item)}${leg.distance_m?` · ${km(leg.distance_m)}`:''}${item.type?.startsWith('scenic_')?` · ${item.direction==='reverse'?t('common.reverse'):t('common.forward')}`:''}`;text.append(title,sub);text.onclick=()=>{state.expandedItemId=state.expandedItemId===item.id?null:item.id;renderRoute();const p=item.place_id&&state.placeMap.get(item.place_id);if(p)selectPlace(p.id,{center:true})};
    const buttons=document.createElement('div');buttons.className='route-buttons';for(const [label,act,titleKey] of [['↑','up','planner.moveUp'],['↓','down','planner.moveDown'],['×','remove','planner.remove']]){const b=document.createElement('button');b.textContent=label;b.title=t(titleKey);b.onclick=()=>routeAction(item,act);buttons.append(b)}row.append(drag,text,buttons);card.append(row);
    if(item.id===state.expandedItemId){const model=expandedItemModel(item,leg),ex=document.createElement('div');ex.className='route-expanded';const details=document.createElement('div');details.textContent=`${routeStopLabel(item)}${model.distance_m?` · ${km(model.distance_m)}`:''}${model.hiddenViaCount?` · ${t('planner.internalVia',{count:model.hiddenViaCount})}`:''}`;ex.append(details);for(const [field,label] of [['position_locked',t('planner.lockPosition')],['direction_locked',t('planner.lockDirection')]]){const l=document.createElement('label'),input=document.createElement('input');input.type='checkbox';input.checked=Boolean(item[field]);input.onchange=()=>patchItem(item,{[field]:input.checked});l.append(input,document.createTextNode(label));ex.append(l)}if(item.type==='scenic_road'||item.type==='scenic_loop'){const b=document.createElement('button');b.className='btn small';b.textContent=t('planner.reverseScenic');b.onclick=()=>patchItem(item,{direction:item.direction==='reverse'?'forward':'reverse'});ex.append(b)}card.append(ex)}
    card.addEventListener('dragstart',()=>{state.dragItemId=item.id;card.classList.add('dragging')});card.addEventListener('dragend',()=>{state.dragItemId=null;card.classList.remove('dragging');$$('.drop-before').forEach(x=>x.classList.remove('drop-before'))});card.addEventListener('dragover',e=>{e.preventDefault();card.classList.add('drop-before')});card.addEventListener('dragleave',()=>card.classList.remove('drop-before'));card.addEventListener('drop',e=>{e.preventDefault();card.classList.remove('drop-before');const src=items.findIndex(x=>x.id===state.dragItemId);if(src>=0&&src!==i)moveItem(state.dragItemId,i)});box.append(card);
  });
  const unresolved=(state.preview?.legs||[]).filter(l=>!l.resolved);$('#routeProblem').classList.toggle('hidden',!unresolved.length);$('#routeProblem').textContent=unresolved.length?`⚠ ${t('planner.unresolvedRoute',{count:unresolved.length})}`:'';$('#routeDistance').textContent=state.preview?.resolved?km(state.preview.total_distance_m):'—';$('#routeCalcStatus').textContent=state.previewBusy?t('planner.calculating'):state.preview?.resolved?t('planner.routeReady'):t('planner.checkRoute');$('#startNavigationBtn').disabled=!canStartNavigation(items,state.preview);
}

async function withRouteMutation(fn,message=t('planner.routeUpdated')){
  if(!state.route)return;saveIndicator(t('planner.savingStatus'),true);
  try{const r=await fn(state.route);state.route=r;$('#routeNameInput').value=r.name;await refreshPreview();renderFilters();renderSearch();renderMap();renderPopover();saveIndicator();if(message)toast(message,()=>withRouteMutation(x=>api.undo(x.id,x.revision),t('planner.changeUndone')));return r}
  catch(e){saveIndicator(t('planner.saveFailed'));if(e.status===409){toast(t('planner.routeChangedElsewhere'));await reloadRoute()}else toast(e.message);throw e}
}
async function addPlaceToRoute(place){
  if(!isPlaceRoutable(place)){toast(t('planner.noRoadAnchor'));return state.route}
  if(routePlaceIds().has(place.id)){toast(t('planner.alreadyInRoute'));return state.route}
  const item={type:'place',place_id:place.id,nav_anchor_point_id:place.navigation?.anchor_point_id??null,stop_type:'stop'};
  return withRouteMutation(r=>api.addItem(r.id,r.revision,item),t('planner.addedToRoute',{name:placeDisplayName(place)}));
}
async function setPlaceDestination(place){
  if(!isPlaceRoutable(place)){toast(t('planner.noRoadAnchor'));return state.route}
  const existing=(state.route?.items||[]).find(i=>i.place_id===place.id);if(existing){await moveItem(existing.id,(state.route.items||[]).length-1);return}
  await addPlaceToRoute(place);
}
async function addTemporary(w,stopType='stop'){
  try{const snap=await api.snap(w.x,w.y||0,w.z);const item={type:'temporary',temporary_x:w.x,temporary_y:w.y||0,temporary_z:w.z,nav_anchor_point_id:snap.anchor_point_id,stop_type:stopType,custom_label:`${t('planner.waypoint')} ${(state.route?.items?.length||0)+1}`};return withRouteMutation(r=>api.addItem(r.id,r.revision,item),stopType==='via'?t('planner.viaAdded'):t('planner.waypointAdded'))}catch(e){toast(e.message)}
}
async function routeAction(item,action){const idx=state.route.items.findIndex(x=>x.id===item.id);if(action==='up'&&idx>0)return moveItem(item.id,idx-1);if(action==='down'&&idx<state.route.items.length-1)return moveItem(item.id,idx+1);if(action==='remove')return withRouteMutation(r=>api.deleteItem(r.id,item.id,r.revision),t('planner.removedFromRoute',{name:routeDisplayLabel(item)}))}
async function moveItem(id,pos){return withRouteMutation(r=>api.patchItem(r.id,id,r.revision,{position:pos}),t('planner.routeOrderUpdated'))}
async function patchItem(item,patch){return withRouteMutation(r=>api.patchItem(r.id,item.id,r.revision,patch),t('planner.routeItemUpdated'))}
async function renameRoute(name){if(!state.route||state.route.read_only||name.trim()===state.route.name)return saveIndicator();return withRouteMutation(r=>api.renameRoute(r.id,r.revision,name.trim()||'Draft Route',false),null)}

function setQuick(key){state.quick[key]=!state.quick[key];persistFilters();renderFilters();renderSearch();renderMap()}
function applyLayerPresetAndRender(preset){state.layerState=applyLayerPreset(state.layerState,preset);persistLayers();renderFilters();renderMap()}
function syncFacetCheckboxes(){for(const x of $$('.map-filter')){const set=x.name==='surface'?state.facets.surfaces:state.facets.sources;x.checked=set.has(x.value)}}
function onFacetChange(input){const set=input.name==='surface'?state.facets.surfaces:state.facets.sources;input.checked?set.add(input.value):set.delete(input.value);persistFilters();renderFilters();renderSearch();renderMap()}

function downloadJson(doc,name){const blob=new Blob([JSON.stringify(doc,null,2)],{type:'application/json'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}
async function readJsonFile(input){const file=input.files?.[0];if(!file)return null;try{return JSON.parse(await file.text())}finally{input.value=''}}
async function refreshDiagnostics(){try{const d=await api.diagnostics();$('#diagnosticsStatus').textContent=t('planner.catalogValid',{places:d.places,blocks:d.blocks,points:d.graph_points});return d}catch(e){$('#diagnosticsStatus').textContent=t('planner.diagnosticsFailed',{error:e.message});throw e}}
async function applyDiagnostics(){const anchors=$('#showNavAnchors').checked,graphOn=$('#showDirectedGraph').checked;if((anchors||graphOn)&&!diagnosticsGraph)diagnosticsGraph=await api.navgraph();map.setDiagnostics({graph:diagnosticsGraph,showAnchors:anchors,showGraph:graphOn})}

async function showSavedRoutes(){
  const data=await api.routes(),box=$('#savedRoutesList');box.replaceChildren();const groups=[[t('planner.routeGroupBuiltin'),data.built_in||[]],[t('planner.routeGroupSaved'),data.routes||[]]];
  for(const [label,routes] of groups){if(!routes.length)continue;const h=document.createElement('div');h.className='saved-route-group-title';h.textContent=label;box.append(h);for(const r of routes){const row=document.createElement('div');row.className='saved-route-row'+(r.read_only?' read-only':'');const info=document.createElement('div'),name=document.createElement('b'),meta=document.createElement('div');name.textContent=r.name;meta.className='route-kind';meta.textContent=r.read_only?t('planner.builtinReadOnly'):`${t('planner.revision',{revision:r.revision})}${r.is_draft?` · ${t('planner.draft')}`:''}`;info.append(name,meta);const open=document.createElement('button');open.className='btn small';open.textContent=r.id===state.route?.id?t('common.active'):t('common.open');open.disabled=r.id===state.route?.id;open.onclick=async()=>{await api.setActiveRoute(r.id);$('#savedRoutesDrawer').classList.add('hidden');await reloadRoute()};row.append(info,open);box.append(row)}}$('#savedRoutesDrawer').classList.remove('hidden');
}
async function createPlaceAt(w){const name=prompt(t('planner.placeName'));if(!name)return;try{const p=await api.createUserPlace({name,x:w.x,y:w.y||0,z:w.z,category:'my_place'});await reloadPlaces();selectPlace(p.id,{center:true});toast(t('planner.userPlaceSaved',{name:p.name}))}catch(e){toast(e.message)}}
function fitRoute(){const pts=(state.preview?.geometry||[]).map(p=>({x:p[1],z:p[3]}));if(pts.length)map.fitWorldPoints(pts)}

function keyboard(e){
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='f'){e.preventDefault();$('#placeSearch').focus();return}
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='z'){e.preventDefault();$('#undoBtn').click();return}
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='y'){e.preventDefault();$('#redoBtn').click();return}
  if(e.key==='Escape'){state.addPlaceMode=null;state.searchQuery='';state.searchRevealId=null;$('#placeSearch').value='';$('#mapHint').textContent=t('planner.mapHint');for(const id of ['savedRoutesDrawer','addPlaceDrawer','plannerMenuDrawer'])$('#'+id)?.classList.add('hidden');map.closeContext();closePopover();renderSearch();renderMap()}
  if(e.key==='Delete'&&state.expandedItemId){const it=state.route?.items?.find(x=>x.id===state.expandedItemId);if(it)routeAction(it,'remove')}
}

function bindPanelResize(){
  const root=document.documentElement,savedL=Number(localStorage.getItem('plannerLibraryWidth')),savedR=Number(localStorage.getItem('plannerRouteWidth'));if(savedL>=270&&savedL<=520)root.style.setProperty('--library-width',`${savedL}px`);if(savedR>=310&&savedR<=650)root.style.setProperty('--route-width',`${savedR}px`);
  const bind=(el,side)=>{el.addEventListener('pointerdown',e=>{e.preventDefault();el.setPointerCapture?.(e.pointerId);el.classList.add('dragging');const start=e.clientX,prop=side==='left'?'--library-width':'--route-width',current=parseFloat(getComputedStyle(root).getPropertyValue(prop))||(side==='left'?310:360);const move=ev=>{const delta=ev.clientX-start,v=Math.round(clamp(current+(side==='left'?delta:-delta),side==='left'?270:310,side==='left'?520:650));root.style.setProperty(prop,`${v}px`);localStorage.setItem(side==='left'?'plannerLibraryWidth':'plannerRouteWidth',String(v));map.render()};const up=()=>{el.classList.remove('dragging');window.removeEventListener('pointermove',move);window.removeEventListener('pointerup',up)};window.addEventListener('pointermove',move);window.addEventListener('pointerup',up,{once:true})})};bind($('#libraryResizer'),'left');bind($('#routeResizer'),'right');
}

function bind(){
  const search=$('#placeSearch');search.oninput=()=>{clearTimeout(searchTimer);searchTimer=setTimeout(()=>{state.searchQuery=search.value;state.library=reduceLibrary(state.library,{type:'query',value:search.value});if(!search.value.trim())state.searchRevealId=null;renderFilters();renderSearch();renderMap()},90)};
  for(const [id,key] of [['favoritesFilter','favorites'],['scenicFilter','scenic'],['photosFilter','photos'],['inRouteFilter','inRoute']])$('#'+id).onclick=()=>setQuick(key);
  $('#layersRecommended').onclick=()=>applyLayerPresetAndRender('recommended');$('#layersEnableAll').onclick=()=>applyLayerPresetAndRender('all');$('#layersDisableAll').onclick=()=>applyLayerPresetAndRender('none');
  $('#layersCollapseAll').onclick=()=>{state.layerState=setAllGroupsCollapsed(state.layerState,true);persistLayers();renderFilters()};
  $('#layersExpandAll').onclick=()=>{state.layerState=setAllGroupsCollapsed(state.layerState,false);persistLayers();renderFilters()};
  for(const x of $$('.map-filter'))x.onchange=()=>onFacetChange(x);
  $('#savedRoutesBtn').onclick=showSavedRoutes;$('#closeSavedRoutes').onclick=()=>$('#savedRoutesDrawer').classList.add('hidden');$('#plannerMenuBtn').onclick=()=>{$('#plannerMenuDrawer').classList.remove('hidden');refreshDiagnostics().catch(()=>{})};$('#closePlannerMenu').onclick=()=>$('#plannerMenuDrawer').classList.add('hidden');
  $('#exportUserData').onclick=async()=>downloadJson(await api.backupExport(),'fh6-navigator-backup.json');$('#importUserData').onclick=()=>$('#backupFile').click();$('#exportRoute').onclick=async()=>downloadJson(await api.routeExport(state.route.id),`${(state.route.name||'route').replace(/[^a-z0-9_-]+/gi,'_')}.fh6route`);$('#importRoute').onclick=()=>$('#routeFile').click();
  $('#backupFile').onchange=async e=>{try{const doc=await readJsonFile(e.target);if(!doc)return;const out=await api.backupImport(doc);toast(`${t('planner.backupImported',{count:out.imported_route_ids?.length||0})}${out.warnings?.length?` · ${t('planner.warningCount',{count:out.warnings.length})}`:''}`);await reloadPlaces()}catch(err){toast(err.message)}};
  $('#routeFile').onchange=async e=>{try{const doc=await readJsonFile(e.target);if(!doc)return;const out=await api.routeImport(doc);await api.setActiveRoute(out.route.id);$('#plannerMenuDrawer').classList.add('hidden');await reloadRoute();await reloadPlaces();toast(`${t('planner.routeImported')}${out.warnings?.length?` · ${t('planner.warningCount',{count:out.warnings.length})}`:''}`)}catch(err){toast(err.message)}};
  $('#showNavAnchors').onchange=()=>applyDiagnostics().catch(e=>toast(e.message));$('#showDirectedGraph').onchange=()=>applyDiagnostics().catch(e=>toast(e.message));
  $('#newRouteBtn').onclick=async()=>{state.route=await api.createRoute();state.preview=null;$('#routeNameInput').value=state.route.name;await refreshPreview();renderAll()};$('#duplicateRouteBtn').onclick=async()=>{state.route=await api.duplicateRoute(state.route.id);await api.setActiveRoute(state.route.id);await refreshPreview();renderAll()};$('#undoBtn').onclick=()=>withRouteMutation(r=>api.undo(r.id,r.revision),t('planner.changeUndone'));$('#redoBtn').onclick=()=>withRouteMutation(r=>api.redo(r.id,r.revision),t('planner.changeRedone'));
  $('#routeNameInput').oninput=e=>{clearTimeout(renameTimer);saveIndicator(t('planner.savingStatus'),true);renameTimer=setTimeout(()=>renameRoute(e.target.value),650)};$('#routeNameInput').onkeydown=e=>{if(e.key==='Enter'){e.target.blur();renameRoute(e.target.value)}};$('#optimizeBtn').onclick=()=>withRouteMutation(r=>api.optimize(r.id,r.revision,{objective:'fastest',keep_final:true,choose_orientation:true}),t('planner.routeOptimized'));$('#reverseBtn').onclick=()=>withRouteMutation(r=>api.reverse(r.id,r.revision,'cancel'),t('planner.routeReversed'));
  $('#mapZoomIn').onclick=()=>map.zoomBy(1);$('#mapZoomOut').onclick=()=>map.zoomBy(-1);$('#mapFitRoute').onclick=fitRoute;$('#collapseLibrary').onclick=()=>document.body.classList.toggle('library-collapsed');$('#collapseRoute').onclick=()=>document.body.classList.toggle('route-collapsed');$('#browseFeaturedBtn').onclick=()=>{state.quick.scenic=true;persistFilters();renderFilters();renderMap();toast(t('planner.scenicEnabled'))};
  $('#addPlaceBtn').onclick=()=>$('#addPlaceDrawer').classList.remove('hidden');$('#closeAddPlace').onclick=()=>$('#addPlaceDrawer').classList.add('hidden');$('#pickPlaceOnMap').onclick=()=>{state.addPlaceMode='pick';$('#addPlaceDrawer').classList.add('hidden');$('#mapHint').textContent=t('planner.clickToPlace');toast(t('planner.clickMapDestination'))};
  $('#placeAtCurrentCar').onclick=async()=>{try{const telemetry=await api.telemetry();const p=telemetry.packet;if(!telemetry.connected||!Number.isFinite(p?.positionX)||!Number.isFinite(p?.positionZ))throw new Error(t('planner.telemetryDisconnected'));$('#addPlaceDrawer').classList.add('hidden');await createPlaceAt({x:p.positionX,y:p.positionY||0,z:p.positionZ})}catch(e){toast(e.message)}};
  $('#saveCoordinatePlace').onclick=async()=>{const x=Number($('#placeCoordX').value),z=Number($('#placeCoordZ').value);if(!Number.isFinite(x)||!Number.isFinite(z))return toast(t('planner.invalidCoordinates'));$('#addPlaceDrawer').classList.add('hidden');await createPlaceAt({x,y:0,z})};
  for(const b of $$('#mapContext [data-map-action]'))b.onclick=async()=>{const w={x:Number($('#mapContext').dataset.x),y:Number($('#mapContext').dataset.y),z:Number($('#mapContext').dataset.z)};map.closeContext();if(b.dataset.mapAction==='destination'||b.dataset.mapAction==='waypoint')await addTemporary(w,'stop');else if(b.dataset.mapAction==='via')await addTemporary(w,'via');else if(b.dataset.mapAction==='save')await createPlaceAt(w)};
  $('#startNavigationBtn').onclick=async()=>{try{const snap=await api.navigationStart(state.route.id);toast(t('planner.navigationStarted',{name:snap.route?.name||state.route.name}));const w=window.open('/','fh6-drive');if(w)w.focus();$('#startNavigationBtn').textContent=t('planner.navigationActive')}catch(e){toast(e.message)}};
  document.addEventListener('keydown',keyboard);
  api.events((type,p)=>{if(type==='route.updated'||type==='active_route.updated'){if(type==='active_route.updated'||p.route_id===state.route?.id)reloadRoute()}else if(type==='favorite.updated'||type==='place.updated')reloadPlaces();else if(type==='navigation.updated'){api.navigationActive().then(s=>{$('#startNavigationBtn').textContent=s?t('planner.navigationActive'):t('planner.startNavigation')}).catch(()=>{})}},online=>{$('#driveStatus').textContent=online?`● ${t('planner.syncConnected')}`:`○ ${t('planner.syncReconnecting')}`;$('#driveStatus').className='connection-chip '+(online?'online':'offline')});
}

async function bootstrap(){
  applyTranslations(document);
  installTooltips(document);
  await loadPlaceNames();
  window.addEventListener('fh6:localechange',()=>{
    rebuildLocalizedLibrary();
    applyTranslations(document);
    renderAll();
    syncFacetCheckboxes();
    $('#mapHint').textContent=state.addPlaceMode==='pick'?t('planner.clickToPlace'):t('planner.mapHint');
    api.navigationActive().then(s=>{$('#startNavigationBtn').textContent=s?t('planner.navigationActive'):t('planner.startNavigation')}).catch(()=>{});
  });
  await loadAll();
}

syncFacetCheckboxes();makeMap();bindPanelResize();bind();bootstrap().catch(e=>{console.error(e);toast(t('planner.failedLoad',{error:e.message}))});
