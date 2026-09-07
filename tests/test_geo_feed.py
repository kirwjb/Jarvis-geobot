import pytest

from src.routers import geo_feed


def test_categories_expand_ui_tags():
    result = geo_feed.categories(["museum", "nature"])
    assert "museum" in result
    assert "park" in result
    assert "viewpoint" in result


def test_normalize_category_handles_russian_labels():
    assert geo_feed.normalize_category("Музей") == "museum"
    assert geo_feed.normalize_category("Собор") == "church"
    assert geo_feed.normalize_category("Замок") == "castle"
    assert geo_feed.normalize_category("unknown") == "misc"


def test_place_dict_uses_only_external_photo_url():
    class Place:
        place_id = "osm:node:1"
        name = "Test"
        city = "Минск"
        region = "Минская область"
        address = "Street 1"
        category = "museum"
        lat = 53.9
        lon = 27.56
        hours = None
        phone = None

    class Photo:
        original_url = "https://upload.wikimedia.org/example.jpg"

    result = geo_feed.place_dict(Place(), Photo())
    assert result["image_url"] == Photo.original_url
    assert result["images"] == {"thumb": Photo.original_url, "medium": Photo.original_url, "original": Photo.original_url}
    assert not result["images"]["thumb"].startswith("/media/")


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
    monkeypatch.setattr(geo_feed, "get_attractions_osm", lambda *args, **kwargs: [])

    class Session:
        async def execute(self, *args, **kwargs):
            raise AssertionError("DB should not be queried for an empty import")

    await geo_feed.ensure_city_data(Session(), "Минск", "Минская область")
    assert redis.set_calls == []
