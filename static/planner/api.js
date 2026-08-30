async function request(path,options={}){
  const headers={'Accept':'application/json',...(options.body?{'Content-Type':'application/json'}:{}),...(options.headers||{})};
  const res=await fetch(path,{...options,headers,body:options.body&&typeof options.body!=='string'?JSON.stringify(options.body):options.body});
  const text=await res.text(); let data={}; try{data=text?JSON.parse(text):{}}catch{data={error:text||res.statusText}}
  if(!res.ok){const e=new Error(data.detail||data.error||`HTTP ${res.status}`);e.status=res.status;e.data=data;throw e} return data;
}
export const api={
  telemetry:()=>request('/api/telemetry'),
  places:(mode='recommended')=>request(`/api/places?mode=${encodeURIComponent(mode)}`),
  place:id=>request(`/api/places/${encodeURIComponent(id)}`),
  favorite:(id,on)=>request(`/api/favorites/${encodeURIComponent(id)}`,{method:on?'POST':'DELETE'}),
  createUserPlace:data=>request('/api/user-places',{method:'POST',body:data}),
  updateUserPlace:(id,data)=>request(`/api/user-places/${encodeURIComponent(id)}`,{method:'PATCH',body:data}),
  deleteUserPlace:(id,force=false)=>request(`/api/user-places/${encodeURIComponent(id)}`,{method:'DELETE',body:{force}}),
  snap:(x,y,z)=>request(`/api/snap?x=${x}&y=${y}&z=${z}`),
  routes:()=>request('/api/routes'), activeRoute:()=>request('/api/routes/active'), route:id=>request(`/api/routes/${id}`),
  createRoute:(name='Draft Route',is_draft=true)=>request('/api/routes',{method:'POST',body:{name,is_draft,make_active:true}}),
  renameRoute:(id,revision,name,make_saved=false)=>request(`/api/routes/${id}`,{method:'PUT',body:{expected_revision:revision,name,make_saved}}),
  duplicateRoute:id=>request(`/api/routes/${id}/duplicate`,{method:'POST'}), setActiveRoute:id=>request(`/api/routes/${id}/active`,{method:'POST'}),
  addItem:(id,revision,item,position)=>request(`/api/routes/${id}/items`,{method:'POST',body:{expected_revision:revision,item,position}}),
  patchItem:(rid,iid,revision,patch)=>request(`/api/routes/${rid}/items/${iid}`,{method:'PATCH',body:{expected_revision:revision,...patch}}),
  deleteItem:(rid,iid,revision)=>request(`/api/routes/${rid}/items/${iid}`,{method:'DELETE',body:{expected_revision:revision}}),
  undo:(id,revision)=>request(`/api/routes/${id}/undo`,{method:'POST',body:{expected_revision:revision}}), redo:(id,revision)=>request(`/api/routes/${id}/redo`,{method:'POST',body:{expected_revision:revision}}),
  reverse:(id,revision,policy='cancel')=>request(`/api/routes/${id}/reverse`,{method:'POST',body:{expected_revision:revision,policy}}),
  optimize:(id,revision,opts={})=>request(`/api/routes/${id}/optimize`,{method:'POST',body:{expected_revision:revision,...opts}}),
  preview:(id,revision,startAnchor=null)=>request(`/api/routes/${id}/preview${startAnchor==null?'':`?start_anchor=${startAnchor}`}`),
  navigationActive:()=>request('/api/navigation/active'),
  navigationStart:(route_id,start_anchor=null)=>request('/api/navigation/start',{method:'POST',body:{route_id,start_anchor}}),
  navigationSkip:(session_id=null)=>request('/api/navigation/skip',{method:'POST',body:{session_id}}),
  navigationPrevious:(session_id=null)=>request('/api/navigation/previous',{method:'POST',body:{session_id}}),
  navigationStop:(session_id=null)=>request('/api/navigation/stop',{method:'POST',body:{session_id}}),
  backupExport:()=>request('/api/backup/export'),
  backupImport:doc=>request('/api/backup/import',{method:'POST',body:doc}),
  routeExport:id=>request(`/api/routes/${id}/export`),
  routeImport:doc=>request('/api/routes/import',{method:'POST',body:doc}),
  diagnostics:()=>request('/api/diagnostics'),
  navgraph:()=>request('/api/navgraph'),
  events(onEvent,onStatus){const es=new EventSource('/api/events'); const names=['route.updated','active_route.updated','favorite.updated','place.updated','navigation.updated']; for(const n of names)es.addEventListener(n,e=>onEvent?.(n,JSON.parse(e.data))); es.onopen=()=>onStatus?.(true);es.onerror=()=>onStatus?.(false);return es;}
};
export {request};
