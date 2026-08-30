from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path


GRAND_TOUR_ID = 'builtin.grand_tour_japan'


def _norm(value: str | None) -> str:
    return ' '.join((value or '').strip().casefold().split())


class BuiltinRouteProvider:
    """Build immutable Planner routes from release-owned static definitions."""

    def __init__(self, grand_tour_path: Path, scenic_catalog_path: Path):
        self.grand_tour_path = Path(grand_tour_path)
        self.scenic_catalog_path = Path(scenic_catalog_path)
        self._routes = {GRAND_TOUR_ID: self._load_grand_tour()}

    def _load_grand_tour(self) -> dict:
        route_doc = json.loads(self.grand_tour_path.read_text(encoding='utf-8'))
        scenic_doc = json.loads(self.scenic_catalog_path.read_text(encoding='utf-8'))
        places = scenic_doc.get('places', []) if isinstance(scenic_doc, dict) else []
        by_name: dict[str, dict] = {}
        for place in places:
            for value in [place.get('name'), *(place.get('aliases') or [])]:
                key = _norm(value)
                if key:
                    by_name.setdefault(key, place)

        items = []
        unresolved = []
        for position, waypoint in enumerate(route_doc.get('waypoints') or []):
            candidates = [waypoint.get('game'), waypoint.get('name')]
            place = next((by_name.get(_norm(value)) for value in candidates if by_name.get(_norm(value))), None)
            if place is None:
                unresolved.append(waypoint.get('game') or waypoint.get('name') or f'#{position + 1}')
                continue
            anchor = (place.get('navigation') or {}).get('anchor_point_id')
            if not isinstance(anchor, int):
                unresolved.append(place.get('name') or f'#{position + 1}')
                continue
            items.append({
                'id': f'{GRAND_TOUR_ID}.item.{position + 1:02d}',
                'route_id': GRAND_TOUR_ID,
                'position': position,
                'type': 'place',
                'place_id': place.get('id'),
                'temporary_x': None,
                'temporary_y': None,
                'temporary_z': None,
                'nav_anchor_point_id': anchor,
                'scenic_block_id': None,
                'direction': None,
                'stop_type': 'stop',
                'position_locked': False,
                'direction_locked': False,
                'custom_label': place.get('name'),
            })
        if unresolved:
            raise ValueError('Grand Tour contains unresolved places: ' + ', '.join(unresolved))
        if not items:
            raise ValueError('Grand Tour contains no usable waypoints')
        return {
            'id': GRAND_TOUR_ID,
            'name': 'Grand Tour Japan',
            'is_draft': False,
            'revision': 0,
            'created_at': None,
            'updated_at': None,
            'last_opened_at': None,
            'read_only': True,
            'built_in': True,
            'loop': bool(route_doc.get('loop')),
            'items': items,
        }

    def has(self, route_id: str) -> bool:
        return route_id in self._routes

    def get(self, route_id: str) -> dict:
        if route_id not in self._routes:
            raise KeyError(route_id)
        return deepcopy(self._routes[route_id])

    def list_routes(self) -> list[dict]:
        return [deepcopy(route) for route in self._routes.values()]
