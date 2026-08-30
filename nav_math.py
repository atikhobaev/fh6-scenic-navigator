"""Coordinate math for FH6 Scenic Navigator."""
from __future__ import annotations
import math

TILE_ZOOM = 14
CAL_A_WORLD = (-119.49154, 3888.595)
CAL_A_PIX = (2089486.0, 2087415.0)
CAL_B_WORLD = (-7104.7695, -1863.08)
CAL_B_PIX = (2086885.0, 2089556.0)

_MX = (CAL_B_PIX[0] - CAL_A_PIX[0]) / (CAL_B_WORLD[0] - CAL_A_WORLD[0])
_MZ = (CAL_B_PIX[1] - CAL_A_PIX[1]) / (CAL_B_WORLD[1] - CAL_A_WORLD[1])
_BX = CAL_A_PIX[0] - _MX * CAL_A_WORLD[0]
_BY = CAL_A_PIX[1] - _MZ * CAL_A_WORLD[1]
PX_PER_WORLD_M = (abs(_MX) + abs(_MZ)) / 2.0


def world_to_pixel(world_x: float, world_z: float) -> tuple[float, float]:
    return _MX * world_x + _BX, _MZ * world_z + _BY


def pixel_to_world(pixel_x: float, pixel_y: float) -> tuple[float, float]:
    return (pixel_x - _BX) / _MX, (pixel_y - _BY) / _MZ


def hub_to_pixel(lat: float, lng: float) -> tuple[float, float]:
    """MapGenie/Hub WebMercator lat/lng -> max-zoom (z14) pixel."""
    world_size = float(256 * (2**TILE_ZOOM))
    lat_rad = math.radians(lat)
    x = (lng + 180.0) / 360.0 * world_size
    y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * world_size
    return x, y


def pixel_distance_to_world_m(pixel_distance: float) -> float:
    return pixel_distance / PX_PER_WORLD_M


def distance_point_to_segment_px(p, a, b) -> float:
    px, py = p
    ax, ay = a
    bx, by = b
    abx, aby = bx - ax, by - ay
    denom = abx * abx + aby * aby
    if denom == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * abx + (py - ay) * aby) / denom
    t = max(0.0, min(1.0, t))
    qx, qy = ax + t * abx, ay + t * aby
    return math.hypot(px - qx, py - qy)
