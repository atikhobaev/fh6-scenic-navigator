import struct
import unittest

from telemetry import parse_packet


class PacketParserTests(unittest.TestCase):
    def test_rejects_short_packet(self):
        self.assertIsNone(parse_packet(b'\x00' * 100))

    def test_parses_fields_needed_by_navigator(self):
        data = bytearray(323)
        struct.pack_into('<i', data, 0, 1)
        struct.pack_into('<f', data, 16, 5234.5)
        struct.pack_into('<f', data, 56, 1.25)
        struct.pack_into('<f', data, 244, -119.49154)
        struct.pack_into('<f', data, 252, 3888.595)
        struct.pack_into('<f', data, 256, 27.7777778)
        struct.pack_into('<B', data, 315, 200)
        struct.pack_into('<B', data, 316, 17)
        struct.pack_into('<B', data, 319, 4)

        p = parse_packet(bytes(data))
        self.assertIsNotNone(p)
        self.assertTrue(p['isRaceOn'])
        self.assertAlmostEqual(p['rpm'], 5234.5, places=1)
        self.assertAlmostEqual(p['yaw'], 1.25, places=3)
        self.assertAlmostEqual(p['positionX'], -119.49154, places=3)
        self.assertAlmostEqual(p['positionZ'], 3888.595, places=3)
        self.assertAlmostEqual(p['speedKmh'], 100.0, places=2)
        self.assertEqual(p['gear'], 4)
        self.assertEqual(p['throttle'], 200)
        self.assertEqual(p['brake'], 17)


if __name__ == '__main__':
    unittest.main()
