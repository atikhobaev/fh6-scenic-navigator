import {layerForPlace} from './layers.js';

function validLocalMedia(value){
  return typeof value==='string'&&value.startsWith('/media/places/')&&!value.includes('..');
}

export function localPlaceImagePath(place={},kind='full'){
  const values=kind==='thumb'?[place.image_thumb,place.image]:[place.image,place.image_thumb];
  for(const value of values){if(validLocalMedia(value))return value}
  return null;
}

export function isPlaceRoutable(place={}){
  if(!place.navigation)return true;
  return Number.isInteger(place.navigation.anchor_point_id)&&place.navigation.anchor_point_id>=0;
}

export function buildPlacePopoverModel(place={},context={}){
  const layer=layerForPlace(place);
  const image=localPlaceImagePath(place,'full');
  const routable=isPlaceRoutable(place);
  const routeAction=(id,label)=>({id,label,disabled:!routable,reason:routable?null:'No reachable road anchor for this place'});
  const actions=[];
  if(!context.inRoute)actions.push(routeAction('add','ADD TO ROUTE'));
  actions.push(routeAction('destination','SET DESTINATION'));
  actions.push({id:'favorite',label:place.favorite?'UNFAVORITE':'FAVORITE',disabled:false,reason:null});
  if(place.source==='user'){
    actions.push({id:'edit',label:'EDIT',disabled:false,reason:null});
    actions.push({id:'delete',label:'DELETE',disabled:false,reason:null});
  }
  return {
    id:place.id,
    title:place.name||'Place',
    subtitle:[layer?.label,place.source&&String(place.source).replace(/^./,s=>s.toUpperCase())].filter(Boolean).join(' · '),
    image,
    imageThumb:localPlaceImagePath(place,'thumb'),
    compact:!image,
    favorite:Boolean(place.favorite),
    routable,
    actions,
  };
}
