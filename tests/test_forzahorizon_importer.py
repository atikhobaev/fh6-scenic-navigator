import hashlib
import tempfile
import unittest
from pathlib import Path


class ForzaHorizonImporterTests(unittest.TestCase):
    def test_coordinate_less_source_record_stays_evidence_only(self):
        from scripts.import_forzahorizon_community import compile_records
        raw = [{'source_id': 'abc', 'title': 'Hidden Viewpoint', 'category': 'Scenic', 'source_url': 'https://forzahorizon.app/spot/abc'}]
        runtime, evidence = compile_records(raw, coordinates={}, snapper=lambda x,y,z:(1,1.0), media_dir=None)
        self.assertEqual(runtime, [])
        self.assertEqual(evidence[0]['release_status'], 'evidence_only')
        self.assertEqual(evidence[0]['release_reason'], 'missing_proven_coordinates')

    def test_proven_coordinate_is_snapped_and_screenshot_is_cached_locally(self):
        from scripts.import_forzahorizon_community import compile_records, deterministic_image_name
        raw = [{
            'source_id': 'spot-42', 'title': 'Hokubu Viewpoint', 'category': 'Secret Road',
            'source_url': 'https://forzahorizon.app/spot/spot-42',
            'screenshot_url': 'https://cdn.example.test/screenshot.jpg', 'contributor': 'pr0g', 'likes': 3,
        }]
        image_bytes = b'actual-image-bytes-for-test'
        with tempfile.TemporaryDirectory() as td:
            media = Path(td)
            runtime, evidence = compile_records(
                raw,
                coordinates={'spot-42': {'x': 10.0, 'y': 2.0, 'z': 20.0}},
                snapper=lambda x,y,z:(77, 4.25),
                media_dir=media,
                fetcher=lambda url: (image_bytes, 'image/jpeg'),
            )
            self.assertEqual(len(runtime), 1)
            row = runtime[0]
            self.assertEqual(row['source'], 'community')
            self.assertEqual(row['category'], 'secret_road')
            self.assertEqual(row['navigation']['anchor_point_id'], 77)
            self.assertEqual(row['image'], '/media/places/community/' + deterministic_image_name('spot-42', 'image/jpeg'))
            saved = media / deterministic_image_name('spot-42', 'image/jpeg')
            self.assertEqual(saved.read_bytes(), image_bytes)
            self.assertEqual(row['image_attribution']['checksum_sha256'], hashlib.sha256(image_bytes).hexdigest())
            self.assertEqual(evidence[0]['release_status'], 'runtime')

    def test_missing_snap_keeps_proven_coordinate_as_evidence_not_routable_place(self):
        from scripts.import_forzahorizon_community import compile_records
        raw = [{'source_id': 'abc', 'title': 'Spot', 'category': 'Other'}]
        runtime, evidence = compile_records(raw, coordinates={'abc': {'x': 1, 'y': 0, 'z': 2}}, snapper=lambda x,y,z:(None,None), media_dir=None)
        self.assertEqual(runtime, [])
        self.assertEqual(evidence[0]['release_reason'], 'no_wvan_anchor')

    def test_deterministic_image_name_does_not_depend_on_remote_filename(self):
        from scripts.import_forzahorizon_community import deterministic_image_name
        a = deterministic_image_name('same-id', 'image/jpeg')
        b = deterministic_image_name('same-id', 'image/jpeg')
        self.assertEqual(a, b)
        self.assertTrue(a.endswith('.jpg'))
        self.assertNotIn('http', a)


if __name__ == '__main__': unittest.main()
