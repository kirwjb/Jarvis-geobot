import pytest

from src.services import parser_service


def test_minsk_bounds_are_explicit_and_ordered():
    bounds = parser_service.CITY_BBOXES["минск"]
    south, west, north, east = bounds
    assert south < north
    assert west < east
    assert south == pytest.approx(53.75)
    assert north == pytest.approx(54.05)


def test_parse_attractions_supports_nodes_and_ways_and_deduplicates():
    elements = [
        {"type": "node", "id": 1, "lat": 53.9, "lon": 27.56,
         "tags": {"name": "Museum", "tourism": "museum", "addr:street": "Lenina", "addr:housenumber": "1"}},
        {"type": "way", "id": 2, "center": {"lat": 53.91, "lon": 27.57},
         "tags": {"name": "Castle", "historic": "castle"}},
        {"type": "node", "id": 3, "lat": 53.9, "lon": 27.56,
         "tags": {"name": "Museum", "tourism": "museum"}},
        {"type": "node", "id": 4, "lat": None, "lon": 27.5, "tags": {"name": "Invalid"}},
    ]

    places = parser_service._parse_attractions(elements)

    assert len(places) == 2
    assert {place["name"] for place in places} == {"Museum", "Castle"}
    museum = next(place for place in places if place["name"] == "Museum")
    castle = next(place for place in places if place["name"] == "Castle")
    assert museum["address"] == "Lenina, 1"
    assert castle["id"] == "osm:way:2"


def test_build_place_id_is_stable_without_osm_id():
    first = parser_service._build_place_id({}, "Test", 53.9, 27.5)
    second = parser_service._build_place_id({}, "Test", 53.9, 27.5)
    assert first == second
    assert first.startswith("osm:")


@pytest.mark.asyncio
async def test_get_city_bounds_uses_minsk_override_without_http(monkeypatch):
    async def fail(*args, **kwargs):
        raise AssertionError("HTTP lookup should not be needed for Minsk")

    monkeypatch.setattr(parser_service.aiohttp, "ClientSession", fail)
    assert await parser_service.get_city_bounds("Минск") == parser_service.CITY_BBOXES["минск"]
