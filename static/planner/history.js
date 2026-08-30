export function historyLabel(action){return ({add_item:'Add place',move_item:'Move route item',remove_item:'Remove route item',optimize:'Optimize route',reverse:'Reverse route',update_item:'Edit route item',rename_route:'Rename route'}[action]||action||'Route change');}
export function optimisticSnapshot(route){return structuredClone?structuredClone(route):JSON.parse(JSON.stringify(route));}
