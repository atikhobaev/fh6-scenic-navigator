import gzip
import json
import tempfile
import unittest
from pathlib import Path

from planner_database import PlannerDatabase


def write_doc(path, places, version='test'):
    path.write_text(json.dumps({'schema_version': 1, 'catalog_version': version, 'places': places}), encoding='utf-8')


def place(pid='community.a', image=None):
    out = {
        'id': pid,
        'source': 'community',
        'kind': 'point',
        'name': 'Community A',
        'aliases': [],
        'category': 'scenic_spot',
        'subcategory': '',
        'tags': ['community'],
        'position': {'x': 10, 'y': 0, 'z': 20},
        'navigation': {'anchor_point_id': 1, 'snap_distance_m': 2.5},
        'surface': 'unknown',
        'access': 'normal',
        'scenic_score': 3,
        'default_visible': False,
        'featured': False,
        'quality': 'verified',
        'external_source_id': 'src-a',
        'image_source': 'forzahorizon.app',
    }
    if image is not None:
        out['image'] = image
    return out


class CommunityPlacesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.builtin = self.root / 'builtin.json'; self.curated = self.root / 'curated.json'; self.community = self.root / 'community.json'
        write_doc(self.builtin, [], 'builtin'); write_doc(self.curated, [], 'curated')
        self.db = PlannerDatabase(self.root / 'navigator.db'); self.db.initialize()
        self.media = self.root / 'media' / 'places'; self.media.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_places_service_loads_community_catalog_and_reports_version(self):
        from places_service import PlacesService
        write_doc(self.community, [place()], 'community-1')
        svc = PlacesService(self.builtin, self.curated, self.db, community_path=self.community, media_root=self.media)
        rows = svc.list_places('all')
        self.assertEqual([p['id'] for p in rows if p['source'] == 'community'], ['community.a'])
        self.assertEqual(svc.catalog_info()['community_version'], 'community-1')

    def test_runtime_catalog_rejects_remote_and_missing_local_images(self):
        from places_service import CatalogValidationError, PlacesService
        for image in ('https://example.com/photo.jpg', '/media/places/community/missing.jpg', '/media/places/../secret.jpg'):
            with self.subTest(image=image):
                write_doc(self.community, [place(image=image)], 'community-1')
                with self.assertRaises(CatalogValidationError):
                    PlacesService(self.builtin, self.curated, self.db, community_path=self.community, media_root=self.media)

    def test_runtime_catalog_accepts_existing_local_media_path(self):
        from places_service import PlacesService
        folder = self.media / 'community'; folder.mkdir()
        (folder / 'a.jpg').write_bytes(b'jpeg-placeholder-for-test')
        write_doc(self.community, [place(image='/media/places/community/a.jpg')], 'community-1')
        svc = PlacesService(self.builtin, self.curated, self.db, community_path=self.community, media_root=self.media)
        self.assertEqual(svc.get_place('community.a')['image'], '/media/places/community/a.jpg')

    def test_catalog_validator_counts_community_and_rejects_remote_runtime_image(self):
        from catalog_validator import CatalogValidationError, validate_catalogs
        graph = {'format': 'fh6-navgraph-v1', 'points': [[1, 10, 0, 20]], 'segments': [], 'transitions': []}
        community = {'schema_version': 1, 'catalog_version': 'c', 'places': [place()]}
        report = validate_catalogs({'places': []}, {'places': [], 'blocks': [], 'collections': []}, graph, community_doc=community)
        self.assertEqual(report['places'], 1)
        community['places'][0]['image'] = 'https://example.com/x.jpg'
        with self.assertRaises(CatalogValidationError):
            validate_catalogs({'places': []}, {'places': [], 'blocks': [], 'collections': []}, graph, community_doc=community)


if __name__ == '__main__': unittest.main()
