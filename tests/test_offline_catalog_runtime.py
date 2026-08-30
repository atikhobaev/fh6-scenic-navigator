from pathlib import Path


def test_update_map_data_batch_uses_offline_rebuild_only():
    text = Path("update_map_data.bat").read_text(encoding="utf-8").lower()
    assert "tools.places_import.offline_rebuild" in text
    assert "tools.places_import.bootstrap" not in text
    assert "internet is not used" in text


def test_launcher_has_no_runtime_catalog_bootstrap_dependency():
    text = Path("launcher.py").read_text(encoding="utf-8")
    assert "tools.places_import.bootstrap" not in text
    assert "bootstrap_catalog" not in text
    assert "inspect_bundled_catalog" in text


def test_offline_rebuild_exposes_visible_staged_progress():
    text = Path("tools/places_import/offline_rebuild.py").read_text(encoding="utf-8")
    for step in range(1, 6):
        assert f"[{step}/5]" in text
    assert "flush=True" in text


def test_offline_rebuild_uses_bundled_snapshots_and_publishes_valid_catalogs(tmp_path):
    import shutil
    from tools.places_import.offline_rebuild import rebuild_offline_catalogs

    data = tmp_path / "static" / "data"
    data.mkdir(parents=True)
    shutil.copyfile("static/data/fh6_navgraph_v1.json.gz", data / "fh6_navgraph_v1.json.gz")
    shutil.copyfile("static/data/scenic_catalog.json", data / "scenic_catalog.json")
    shutil.copyfile("static/data/fh6_roads.json", data / "fh6_roads.json")
    result = rebuild_offline_catalogs(root=tmp_path, catalog_version="offline-test")
    assert result["internet_used"] is False
    assert result["official_places"] == 796
    assert result["curated_places"] == 27
    assert result["total_places"] == 823
    assert (data / "builtin_places.json").is_file()
    assert (data / "scenic_catalog.json").is_file()


def test_offline_rebuild_rolls_back_if_publication_fails_midway(tmp_path, monkeypatch):
    import json
    import shutil
    import tools.places_import.offline_rebuild as rebuild

    data = tmp_path / "static" / "data"
    data.mkdir(parents=True)
    shutil.copyfile("static/data/fh6_navgraph_v1.json.gz", data / "fh6_navgraph_v1.json.gz")
    shutil.copyfile("static/data/scenic_catalog.json", data / "scenic_catalog.json")
    shutil.copyfile("static/data/fh6_roads.json", data / "fh6_roads.json")
    (data / "builtin_places.json").write_text('{"sentinel":"old"}\n', encoding="utf-8")
    old_builtin = (data / "builtin_places.json").read_bytes()
    old_curated = (data / "scenic_catalog.json").read_bytes()

    real_replace = rebuild.os.replace
    calls = {"n": 0}
    def flaky_replace(src, dst):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("simulated publish failure")
        return real_replace(src, dst)
    monkeypatch.setattr(rebuild.os, "replace", flaky_replace)

    try:
        rebuild.rebuild_offline_catalogs(root=tmp_path, catalog_version="rollback-test")
    except OSError:
        pass
    else:
        raise AssertionError("expected simulated publication failure")

    assert (data / "builtin_places.json").read_bytes() == old_builtin
    assert (data / "scenic_catalog.json").read_bytes() == old_curated
