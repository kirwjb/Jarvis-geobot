import pytest
from types import SimpleNamespace

from src.routers import api_integrated


class FakeResult:
    def __init__(self, places):
        self.places = places

    def scalars(self):
        return self

    def all(self):
        return self.places


class FakeSession:
    def __init__(self, places):
        self.places = places

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        pass

    async def execute(self, query):
        return FakeResult(self.places)


class FakeSessionFactory:
    def __init__(self, places):
        self.places = places

    def __call__(self):
        return FakeSession(self.places)


def make_place(
    place_id,
    name,
    lat,
    lon,
):
    return SimpleNamespace(
        place_id=place_id,
        name=name,
        city="Минск",
        region="Минская область",
        address="",
        category="attraction",
        lat=lat,
        lon=lon,
        hours=None,
        phone=None,
    )


@pytest.mark.asyncio
async def test_build_route_success(monkeypatch):
    places = [
        make_place(
            "p1",
            "Точка 1",
            53.9000,
            27.5600,
        ),
        make_place(
            "p2",
            "Точка 2",
            53.9100,
            27.5800,
        ),
    ]

    monkeypatch.setattr(
        api_integrated,
        "AsyncSessionLocal",
        FakeSessionFactory(places),
    )

    async def fake_distance(
        lat1,
        lon1,
        lat2,
        lon2,
    ):
        return 2.5

    monkeypatch.setattr(
        api_integrated,
        "get_distance_osrm",
        fake_distance,
    )

    monkeypatch.setattr(
        api_integrated,
        "build_google_maps_link",
        lambda points: "https://maps.example/route",
    )

    request = api_integrated.RouteRequest(
        poi_ids=["p1", "p2"],
        optimize=True,
    )

    result = await api_integrated.build_route(request)

    assert result.poi_ids == ["p1", "p2"]
    assert result.google_maps_url == "https://maps.example/route"
    assert result.total_distance_km == 2.5
    assert result.optimized is True


@pytest.mark.asyncio
async def test_build_route_osrm_failure_returns_none_distance(
    monkeypatch,
):
    places = [
        make_place(
            "p1",
            "Точка 1",
            53.9000,
            27.5600,
        ),
        make_place(
            "p2",
            "Точка 2",
            53.9100,
            27.5800,
        ),
    ]

    monkeypatch.setattr(
        api_integrated,
        "AsyncSessionLocal",
        FakeSessionFactory(places),
    )

    async def fake_distance(
        lat1,
        lon1,
        lat2,
        lon2,
    ):
        return None

    monkeypatch.setattr(
        api_integrated,
        "get_distance_osrm",
        fake_distance,
    )

    monkeypatch.setattr(
        api_integrated,
        "build_google_maps_link",
        lambda points: "https://maps.example/route",
    )

    request = api_integrated.RouteRequest(
        poi_ids=["p1", "p2"],
        optimize=True,
    )

    result = await api_integrated.build_route(request)

    assert result.poi_ids == ["p1", "p2"]
    assert result.google_maps_url == "https://maps.example/route"

    # Главное: никакого фейкового расстояния.
    assert result.total_distance_km is None

    assert result.optimized is True


@pytest.mark.asyncio
async def test_build_route_requires_two_points():
    request = api_integrated.RouteRequest(
        poi_ids=["p1"],
        optimize=True,
    )

    with pytest.raises(api_integrated.HTTPException) as exc_info:
        await api_integrated.build_route(request)

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_build_route_requires_two_unique_points(
    monkeypatch,
):
    request = api_integrated.RouteRequest(
        poi_ids=["p1", "p1"],
        optimize=True,
    )

    with pytest.raises(api_integrated.HTTPException) as exc_info:
        await api_integrated.build_route(request)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Need at least 2 unique points"