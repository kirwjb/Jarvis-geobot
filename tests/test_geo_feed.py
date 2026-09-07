from types import SimpleNamespace

import pytest

from src.routers import geo_feed


def test_categories_expand_ui_tags():
    assert geo_feed.categories(["museum", "nature"]) == {"museum", "park", "viewpoint", "ruins"}


def test_normalize_category_handles_russian_labels():
    assert geo_feed.normalize_category("Музей") == "museum"
    assert geo_feed.normalize_category("Собор") == "church"
    assert geo_feed.normalize_category("Замок") == "castle"
    assert geo_feed.normalize_category("unknown") == "misc"


def test_place_dict_exposes_external_photo_without_local_paths():
    place = SimpleNamespace(place_id="osm:node:1", name="Test", city="Минск", region="Минская область", address="Street 1", category="museum", lat=53.9, lon=27.56, hours=None, phone=None)
    photo = SimpleNamespace(original_url="https://upload.wikimedia.org/example.jpg")
    result = geo_feed.place_dict(place, photo)
    assert result["image_url"] == photo.original_url
    assert result["images"] == {"thumb": photo.original_url, "medium": photo.original_url, "original": photo.original_url}
    assert not result["images"]["thumb"].startswith("/media/")


def test_marker_key_is_region_scoped():
    assert geo_feed._marker_key("Минск", "Минская область") != geo_feed._marker_key("Минск", "другая область")


@pytest.mark.asyncio
async def test_ensure_city_data_does_not_mark_empty_import(monkeypatch):
    class Redis:
        def __init__(self):
            self.set_calls = []
        async def get(self, key):
            return None
        async def setex(self, *args):
            self.set_calls.append(args)

    redis = Redis()
    monkeypatch.setattr(geo_feed, "redis_client", redis)
    async def no_data(*args, **kwargs):
        return []
    monkeypatch.setattr(geo_feed, "get_attractions_osm", no_data)
    await geo_feed.ensure_city_data(SimpleNamespace(), "Минск", "Минская область")
    assert redis.set_calls == []


@pytest.mark.asyncio
async def test_marker_read_failure_is_fail_open(monkeypatch):
    class BrokenRedis:
        async def get(self, key):
            raise RuntimeError("redis unavailable")
    monkeypatch.setattr(geo_feed, "redis_client", BrokenRedis())
    assert await geo_feed._marker_exists("test") is False
