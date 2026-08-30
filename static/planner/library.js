import {buildSearchIndex,searchPlaces,activeFilterChips} from './search.js';

export function createLibraryState(places=[],saved={}){
  return {
    places:[...places], index:buildSearchIndex(places), query:saved.query||'', filters:{mode:'recommended',sort:'recommended',...(saved.filters||{})},
    selectedId:saved.selectedId||null, scrollTop:Number(saved.scrollTop)||0, detailOpen:Boolean(saved.detailOpen)
  };
}
export function updatePlaces(state,places){return {...state,places:[...places],index:buildSearchIndex(places)};}
export function libraryResults(state){return searchPlaces(state.index,state.query,state.filters);}
export function libraryChips(state){return activeFilterChips(state.filters);}
export function serializeLibraryState(state){return {query:state.query,filters:state.filters,selectedId:state.selectedId,scrollTop:state.scrollTop,detailOpen:state.detailOpen};}

export function reduceLibrary(state,action){
  switch(action.type){
    case 'query': return {...state,query:action.value};
    case 'filter': return {...state,filters:{...state.filters,[action.key]:action.value}};
    case 'sort': return {...state,filters:{...state.filters,sort:action.value}};
    case 'scroll': return {...state,scrollTop:Number(action.value)||0};
    case 'select': return {...state,selectedId:action.id};
    case 'detail': return {...state,detailOpen:Boolean(action.open)};
    default:return state;
  }
}
export function visibleWindow(scrollTop,viewportHeight,rowHeight,total){
  const overscan=5,start=Math.max(0,Math.floor(scrollTop/rowHeight)-overscan),end=Math.min(total,Math.ceil((scrollTop+viewportHeight)/rowHeight)+overscan);return {start,end,offset:start*rowHeight,totalHeight:total*rowHeight};
}
