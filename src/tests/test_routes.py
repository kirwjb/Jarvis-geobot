import asyncio

import pytest

from src.services.routes_service import get_distance_osrm


class FakeResponse:
    def __init__(
        self,
        status=200,
        data=None,
        text="",
    ):
        self.status = status
        self._data = data or {}
        self._text = text

    async def __aenter__(self):
        return self

    async def __aexit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        pass

    async def json(self):
        return self._data

    async def text(self):
        return self._text


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.request_url = None
        self.request_params = None

    async def __aenter__(self):
        return self

    async def __aexit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        pass

    def get(
        self,
        url,
        params=None,
        timeout=None,
    ):
        self.request_url = url
        self.request_params = params
        return self.response


@pytest.mark.asyncio
async def test_get_distance_osrm_success(
    monkeypatch,
):
    response = FakeResponse(
        status=200,
        data={
            "routes": [
                {
                    "distance": 12500,
                }
            ]
        },
    )

    session = FakeSession(response)

    monkeypatch.setattr(
        "src.services.routes_service.aiohttp.ClientSession",
        lambda: session,
    )

    distance = await get_distance_osrm(
        53.9000,
        27.5600,
        53.9100,
        27.5800,
    )

    assert distance == 12.5

    assert (
        session.request_url
        == "https://router.project-osrm.org/"
        "route/v1/driving/"
        "27.56,53.9;27.58,53.91"
    )

    assert session.request_params == {
        "overview": "false",
        "annotations": "false",
    }


@pytest.mark.asyncio
async def test_get_distance_osrm_no_routes(
    monkeypatch,
):
    response = FakeResponse(
        status=200,
        data={
            "routes": []
        },
    )

    session = FakeSession(response)

    monkeypatch.setattr(
        "src.services.routes_service.aiohttp.ClientSession",
        lambda: session,
    )

    distance = await get_distance_osrm(
        53.9000,
        27.5600,
        53.9100,
        27.5800,
    )

    assert distance is None


@pytest.mark.asyncio
async def test_get_distance_osrm_http_error(
    monkeypatch,
):
    response = FakeResponse(
        status=500,
        text="OSRM error",
    )

    session = FakeSession(response)

    monkeypatch.setattr(
        "src.services.routes_service.aiohttp.ClientSession",
        lambda: session,
    )

    distance = await get_distance_osrm(
        53.9000,
        27.5600,
        53.9100,
        27.5800,
    )

    assert distance is None


@pytest.mark.asyncio
async def test_get_distance_osrm_timeout(
    monkeypatch,
):
    class TimeoutSession:
        async def __aenter__(self):
            return self

        async def __aexit__(
            self,
            exc_type,
            exc_value,
            traceback,
        ):
            pass

        def get(
            self,
            url,
            params=None,
            timeout=None,
        ):
            raise asyncio.TimeoutError

    monkeypatch.setattr(
        "src.services.routes_service.aiohttp.ClientSession",
        TimeoutSession,
    )

    distance = await get_distance_osrm(
        53.9000,
        27.5600,
        53.9100,
        27.5800,
    )

    assert distance is None