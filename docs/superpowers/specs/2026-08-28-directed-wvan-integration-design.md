# Directed WVAN Integration Design

Use the user-supplied Brio_00.nav as the authoritative traffic graph source. Compile it offline into `fh6-navgraph-v1`, preserving source SHA and capability flags. LabsGG roads remain only for surface overlay and POI ordering. Active guidance, blue scenic legs, manual target routing, map matching and rerouting use the WVAN graph and fail closed if unavailable.

Traffic legality comes from ordered WVAN sections plus `oneway_forward`, exact shared NavPoint IDs, and explicit `no_right_turn`. Immediate reverse/U-turn transitions are forbidden because WVAN `uturn` numeric semantics are not yet proven; legal reversal through a loop/interchange remains possible via normal directed transitions.

Runtime matching scores directed segments using X/Z distance, yaw/bearing error and previous-segment continuity. Persistent off-route state beyond 45 m for 800 ms triggers rerouting to the same active POI. UI states are `ПЕРЕСТРАИВАЮ МАРШРУТ…` and `МАРШРУТ НЕ НАЙДЕН ПО РАЗРЕШЁННЫМ НАПРАВЛЕНИЯМ`.
