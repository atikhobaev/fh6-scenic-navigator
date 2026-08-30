import struct
import unittest

from scripts.validate_portable_exe import inspect_pe


class PortableLauncherPETests(unittest.TestCase):
    def test_inspect_pe_reports_windows_gui_pe32plus(self):
        data = bytearray(512)
        data[0:2] = b'MZ'
        pe_offset = 0x80
        struct.pack_into('<I', data, 0x3C, pe_offset)
        data[pe_offset:pe_offset+4] = b'PE\0\0'
        # COFF file header: x64 machine, one section, optional header size 0xF0.
        struct.pack_into('<HHIIIHH', data, pe_offset + 4, 0x8664, 1, 0, 0, 0, 0xF0, 0x0022)
        opt = pe_offset + 24
        struct.pack_into('<H', data, opt, 0x20B)  # PE32+
        struct.pack_into('<H', data, opt + 68, 2)  # IMAGE_SUBSYSTEM_WINDOWS_GUI
        info = inspect_pe(bytes(data))
        self.assertEqual(info['machine'], 0x8664)
        self.assertEqual(info['magic'], 0x20B)
        self.assertEqual(info['subsystem'], 2)

    def test_inspect_pe_rejects_non_pe(self):
        with self.assertRaises(ValueError):
            inspect_pe(b'not-an-exe')


if __name__ == '__main__':
    unittest.main()
