from __future__ import annotations
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class SnapResult:
    point_id: int
    x: float
    y: float
    z: float
    distance_m: float
    route_validated: bool


class NavGraphSnapper:
    """Nearest-X/Z NavPoint lookup for build-time catalog generation.

    The index uses fixed-size X/Z cells. Search expands in square rings and
    stops only when the best hit is closer than the nearest boundary outside
    the searched square, so the result is exact rather than approximate.
    """

    def __init__(self, graph_payload: dict, cell_size: float = 250.0):
        if graph_payload.get("format") != "fh6-navgraph-v1":
            raise ValueError("invalid navgraph format")
        if cell_size <= 0:
            raise ValueError("cell_size must be positive")
        self.cell_size = float(cell_size)
        self.route_validated = bool((graph_payload.get("capabilities") or {}).get("route_validated"))
        self.points: list[tuple[int, float, float, float]] = []
        self.cells: dict[tuple[int, int], list[tuple[int, float, float, float]]] = {}
        for raw in graph_payload.get("points") or []:
            pid, x, y, z = int(raw[0]), float(raw[1]), float(raw[2]), float(raw[3])
            p = (pid, x, y, z)
            self.points.append(p)
            self.cells.setdefault(self._cell(x, z), []).append(p)
        if not self.points:
            raise ValueError("navgraph has no points")
        xs = [c[0] for c in self.cells]
        zs = [c[1] for c in self.cells]
        self._min_cx, self._max_cx = min(xs), max(xs)
        self._min_cz, self._max_cz = min(zs), max(zs)

    def _cell(self, x: float, z: float) -> tuple[int, int]:
        return (math.floor(x / self.cell_size), math.floor(z / self.cell_size))

    def nearest(self, x: float, z: float) -> SnapResult:
        x, z = float(x), float(z)
        qx, qz = self._cell(x, z)
        max_ring = max(
            abs(qx - self._min_cx), abs(qx - self._max_cx),
            abs(qz - self._min_cz), abs(qz - self._max_cz),
        )
        best = None
        best_d2 = math.inf

        for ring in range(max_ring + 1):
            if ring == 0:
                cells = [(qx, qz)]
            else:
                cells = []
                lo_x, hi_x = qx - ring, qx + ring
                lo_z, hi_z = qz - ring, qz + ring
                for cx in range(lo_x, hi_x + 1):
                    cells.append((cx, lo_z)); cells.append((cx, hi_z))
                for cz in range(lo_z + 1, hi_z):
                    cells.append((lo_x, cz)); cells.append((hi_x, cz))
            for cell in cells:
                for p in self.cells.get(cell, ()):
                    d2 = (p[1] - x) ** 2 + (p[3] - z) ** 2
                    if d2 < best_d2:
                        best, best_d2 = p, d2

            if best is not None:
                left = (qx - ring) * self.cell_size
                right = (qx + ring + 1) * self.cell_size
                bottom = (qz - ring) * self.cell_size
                top = (qz + ring + 1) * self.cell_size
                nearest_outside = min(x - left, right - x, z - bottom, top - z)
                if nearest_outside >= 0 and best_d2 <= nearest_outside ** 2:
                    break

        if best is None:  # Defensive fallback; should be unreachable with non-empty graph.
            best = min(self.points, key=lambda p: (p[1] - x) ** 2 + (p[3] - z) ** 2)
            best_d2 = (best[1] - x) ** 2 + (best[3] - z) ** 2
        return SnapResult(best[0], best[1], best[2], best[3], math.sqrt(best_d2), self.route_validated)
