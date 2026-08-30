import json
from pathlib import Path
from tools.places_import.bootstrap import (
    HUB_CATEGORIES,
    category_from_title,
    extract_mapgenie_map_data,
    parse_hub_category_html,
    records_from_mapgenie,
)


def test_hub_inventory_covers_all_796_markers():
    assert len(HUB_CATEGORIES) == 38
    assert sum(item.count for item in HUB_CATEGORIES) == 796


def test_category_mapping_covers_representative_layers():
    assert category_from_title('Landmark') == 'landmark'
    assert category_from_title('Photo Subject') == 'photo_spot'
    assert category_from_title('XP Board') == 'xp_board'
    assert category_from_title('Dirt Racing Event') == 'rally_race'
    assert category_from_title('Curry Mascot') == 'mascot'
    assert category_from_title('Story Chapter') == 'story'


def test_extract_mapgenie_window_map_data_and_normalize_records():
    payload = {
        'categories': {'10': {'id': 10, 'title': 'Landmark'}},
        'locations': [{
            'id': 568810,
            'category_id': 10,
            'title': 'Hokubu Circuit',
            'latitude': 0.8010,
            'longitude': -0.5709,
            'media': [{'url': 'https://cdn.example/place.jpg'}],
            'description': '<p>Race circuit</p>',
        }],
    }
    html = '<html><script>window.mapData = ' + json.dumps(payload) + ';</script></html>'
    data = extract_mapgenie_map_data(html)
    assert data['locations'][0]['id'] == 568810
    records, media = records_from_mapgenie(data, retrieved_at='2026-08-30')
    assert len(records) == 1
    r = records[0]
    assert r.source_id == '568810'
    assert r.name == 'Hokubu Circuit'
    assert r.category == 'landmark'
    assert r.world_x is not None and r.world_z is not None
    assert media['568810'][0] == 'https://cdn.example/place.jpg'


def test_parse_hub_category_html_extracts_server_rendered_marker():
    html = '''
      <h2>Hokubu (6)</h2>
      <article><h3>Hokubu Circuit</h3>
      <a href="/map?cat=landmark&amp;loc=568810">Show on map</a>
      <span>0.8010, -0.5709</span></article>
    '''
    rows = parse_hub_category_html(html, slug='landmark', provider_category='Landmark', retrieved_at='2026-08-30')
    assert len(rows) == 1
    assert rows[0].source_id == '568810'
    assert rows[0].name == 'Hokubu Circuit'
    assert rows[0].region == 'Hokubu'
    assert rows[0].category == 'landmark'
    assert rows[0].world_x is not None


def test_bootstrap_atomically_builds_catalog_and_local_image(tmp_path):
    import gzip, shutil
    from tools.places_import.bootstrap import bootstrap_catalog
    root=tmp_path
    (root/'static/data').mkdir(parents=True)
    shutil.copyfile('static/data/fh6_navgraph_v1.json.gz',root/'static/data/fh6_navgraph_v1.json.gz')
    payload={
      'categories':{'10':{'id':10,'title':'Landmark'}},
      'locations':[{'id':1,'category_id':10,'title':'Ine','latitude':0.7771,'longitude':-0.4599,'media':[{'url':'https://cdn.example/ine.jpg'}]}]
    }
    page=('<script>window.mapData = '+json.dumps(payload)+';</script>').encode()
    def fetch(url):
      if 'mapgenie.io/forza-horizon-6/maps/japan' in url:return page,'text/html'
      if url=='https://cdn.example/ine.jpg':return b'\xff\xd8\xff\xe0fake','image/jpeg'
      raise AssertionError(url)
    result=bootstrap_catalog(root=root,force=True,fetch=fetch,min_records=1,media_limit=5)
    assert result['status']=='updated'
    doc=json.loads((root/'static/data/builtin_places.json').read_text())
    assert len(doc['places'])==1
    place=doc['places'][0]
    assert place['navigation']['anchor_point_id'] is not None
    assert place['image'].startswith('/media/places/')
    assert (root/'static/media/places'/Path(place['image']).name).is_file()
