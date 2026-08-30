import math
import unittest

from nav_math import (
    hub_to_pixel,
    world_to_pixel,
    pixel_distance_to_world_m,
    distance_point_to_segment_px,
)


class NavMathTests(unittest.TestCase):
    def test_world_calibration_hits_reference_points(self):
        ax, ay = world_to_pixel(-119.49154, 3888.595)
        bx, by = world_to_pixel(-7104.7695, -1863.08)
        self.assertAlmostEqual(ax, 2089486, places=3)
        self.assertAlmostEqual(ay, 2087415, places=3)
        self.assertAlmostEqual(bx, 2086885, places=3)
        self.assertAlmostEqual(by, 2089556, places=3)

    def test_hub_coordinate_to_pixel(self):
        x, y = hub_to_pixel(0.9135, -0.5634)
        self.assertAlmostEqual(x, 2090587.91424, places=4)
        self.assertAlmostEqual(y, 2086508.5026647933, places=3)

    def test_pixel_distance_converts_back_to_world_meters(self):
        self.assertAlmostEqual(pixel_distance_to_world_m(37.23), 100.0, delta=0.2)

    def test_distance_to_line_segment(self):
        d = distance_point_to_segment_px((5, 4), (0, 0), (10, 0))
        self.assertAlmostEqual(d, 4.0)
        d2 = distance_point_to_segment_px((15, 0), (0, 0), (10, 0))
        self.assertAlmostEqual(d2, 5.0)


if __name__ == '__main__':
    unittest.main()
