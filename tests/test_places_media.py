from pathlib import Path
from tools.places_import.media import extract_image_urls, cache_image_bytes


def test_extract_image_urls_finds_nested_media_and_description_images():
    value = {
        'media': [{'url': 'https://cdn.example/a.jpg'}, {'thumbnail': 'https://cdn.example/a-thumb.webp'}],
        'description': '<p>x</p><img src="https://cdn.example/b.png">',
    }
    urls = extract_image_urls(value)
    assert urls[:3] == ['https://cdn.example/a.jpg','https://cdn.example/a-thumb.webp','https://cdn.example/b.png']


def test_cache_image_bytes_keeps_local_asset_even_without_pillow(tmp_path):
    data = b'\xff\xd8\xff\xe0fakejpeg'
    result = cache_image_bytes(data, content_type='image/jpeg', stable_id='builtin.game.landmark.test', media_root=tmp_path, allow_pillow=False)
    assert result['image'].startswith('/media/places/')
    assert result['image_thumb'] == result['image']
    rel = result['image'].removeprefix('/media/places/')
    assert (tmp_path / rel).read_bytes() == data
