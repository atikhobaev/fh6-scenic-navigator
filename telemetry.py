"""Minimal Forza Horizon 6 Car Dash packet parser.

Offsets follow the public FH6 community Car Dash layout used by fh6-tel /
FH6 Oversight Dashboard. We intentionally parse only fields needed by the navigator.
"""
from __future__ import annotations
import struct

MIN_PACKET_SIZE = 323


def _f(data: bytes, offset: int) -> float:
    return struct.unpack_from('<f', data, offset)[0]


def _i(data: bytes, offset: int) -> int:
    return struct.unpack_from('<i', data, offset)[0]


def _b(data: bytes, offset: int) -> int:
    return struct.unpack_from('<B', data, offset)[0]


def parse_packet(data: bytes):
    if len(data) < MIN_PACKET_SIZE:
        return None
    try:
        return {
            'isRaceOn': bool(_i(data, 0)),
            'rpm': _f(data, 16),
            'yaw': _f(data, 56),
            'positionX': _f(data, 244),
            'positionZ': _f(data, 252),
            'speedKmh': _f(data, 256) * 3.6,
            'throttle': _b(data, 315),
            'brake': _b(data, 316),
            'gear': _b(data, 319),
        }
    except struct.error:
        return None
