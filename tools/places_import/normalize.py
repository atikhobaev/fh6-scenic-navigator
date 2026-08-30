from __future__ import annotations
import re
import unicodedata

# Existing production calibration copied exactly from static/routing.js + static/nav_logic.js.
_MAPGENIE_PIXEL_MIN = 2080768.0
_LAB_TO_Z12_A = 0.70688367
_LAB_TO_Z12_B = 0.00036652
_LAB_TO_Z12_C = 1370.9325
_LAB_TO_Z12_D = 0.00004749
_LAB_TO_Z12_E = 0.70754216
_LAB_TO_Z12_F = 1089.5011
_CAL_A_WORLD = (-119.49154, 3888.595)
_CAL_A_PIX = (2089486.0, 2087415.0)
_CAL_B_WORLD = (-7104.7695, -1863.08)
_CAL_B_PIX = (2086885.0, 2089556.0)
_MX = (_CAL_B_PIX[0] - _CAL_A_PIX[0]) / (_CAL_B_WORLD[0] - _CAL_A_WORLD[0])
_MZ = (_CAL_B_PIX[1] - _CAL_A_PIX[1]) / (_CAL_B_WORLD[1] - _CAL_A_WORLD[1])
_BX = _CAL_A_PIX[0] - _MX * _CAL_A_WORLD[0]
_BY = _CAL_A_PIX[1] - _MZ * _CAL_A_WORLD[1]


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    return re.sub(r"\s+", " ", text)


def slug(value: str) -> str:
    return normalize_text(value).replace(" ", "_")


def stable_place_id(source: str, category: str, name: str) -> str:
    prefix = "builtin" if source == "game" else source
    return f"{prefix}.{source}.{slug(category)}.{slug(name)}" if prefix == "builtin" else f"{prefix}.{slug(category)}.{slug(name)}"


def lab_map_ref_to_world(map_x: float, map_y: float) -> tuple[float, float]:
    z12_x = _LAB_TO_Z12_A * float(map_x) + _LAB_TO_Z12_B * float(map_y) + _LAB_TO_Z12_C
    z12_y = _LAB_TO_Z12_D * float(map_x) + _LAB_TO_Z12_E * float(map_y) + _LAB_TO_Z12_F
    pixel_x = _MAPGENIE_PIXEL_MIN + z12_x * 4.0
    pixel_y = _MAPGENIE_PIXEL_MIN + z12_y * 4.0
    world_x = (pixel_x - _BX) / _MX
    world_z = (pixel_y - _BY) / _MZ
    return world_x, world_z
