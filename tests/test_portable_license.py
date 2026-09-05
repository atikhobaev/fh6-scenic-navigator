import unittest
from pathlib import Path
from scripts.build_launcher_payload import ROOT, should_include


class PortableLicenseTests(unittest.TestCase):
    def test_original_license_and_scope_are_included_in_release_payload(self):
        for name in ('LICENSE', 'LICENSE_SCOPE.md', 'THIRD_PARTY_NOTICES.md'):
            with self.subTest(name=name):
                self.assertTrue((ROOT / name).is_file())
                self.assertTrue(should_include(ROOT / name), name)
