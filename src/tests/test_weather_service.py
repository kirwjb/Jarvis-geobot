"""
Unit tests for the Weather Service handling missing/None city
and returning reminders in supported languages (RU / BY).
"""

import json
from unittest.mock import AsyncMock, MagicMock
import pytest
from starlette.requests import Request

from src.services.weather_service import (
    CityNotSelectedError,
    get_city_selection_reminder,
    get_weather,
    is_city_missing,
)
from src.routers.api_integrated import get_weather_endpoint


def test_is_city_missing_detection():
    # None and empty variants
    assert is_city_missing(None) is True
    assert is_city_missing("") is True
    assert is_city_missing("   ") is True

    # Placeholder string variants
    assert is_city_missing("none") is True
    assert is_city_missing("None") is True
    assert is_city_missing("NONE") is True
    assert is_city_missing("null") is True
    assert is_city_missing("Null") is True
    assert is_city_missing("undefined") is True
    assert is_city_missing("0") is True

    # Real city names
    assert is_city_missing("Минск") is False
    assert is_city_missing("Брест") is False
    assert is_city_missing("Grodno") is False


def test_city_selection_reminder_translations():
    # Russian
    reminder_ru = get_city_selection_reminder("ru")
    assert "Сначала выберите город" in reminder_ru
    assert "Путешествия" in reminder_ru

    # Belarusian (by and be)
    reminder_by = get_city_selection_reminder("by")
    assert "Спачатку выберыце горад" in reminder_by
    assert "Падарожжы" in reminder_by

    reminder_be = get_city_selection_reminder("be")
    assert "Спачатку выберыце горад" in reminder_be


@pytest.mark.asyncio
async def test_get_weather_none_city_returns_ru_reminder():
    raw_res = await get_weather(None, lang="ru")
    data = json.loads(raw_res)

    assert data["temp"] is None
    assert data["requires_city_selection"] is True
    assert "Сначала выберите город" in data["description"]
    assert "Путешествия" in data["description"]


@pytest.mark.asyncio
async def test_get_weather_none_string_returns_by_reminder():
    for placeholder in ["none", "None", "null", "undefined", ""]:
        raw_res = await get_weather(placeholder, lang="by")
        data = json.loads(raw_res)

        assert data["temp"] is None
        assert data["requires_city_selection"] is True
        assert "Спачатку выберыце горад" in data["description"]
        assert "Падарожжы" in data["description"]


@pytest.mark.asyncio
async def test_get_weather_raise_on_missing_flag():
    with pytest.raises(CityNotSelectedError) as exc_ru:
        await get_weather(None, lang="ru", raise_on_missing=True)
    assert "Сначала выберите город" in str(exc_ru.value)

    with pytest.raises(CityNotSelectedError) as exc_by:
        await get_weather("none", lang="by", raise_on_missing=True)
    assert "Спачатку выберыце горад" in str(exc_by.value)


@pytest.mark.asyncio
async def test_get_weather_valid_city_calls_provider(monkeypatch):
    mock_payload = {
        "current_condition": [
            {
                "temp_C": "14",
                "weatherDesc": [{"value": "Ясно"}],
                "humidity": "65",
                "windspeedKmph": "18",
                "pressure": "1015",
            }
        ]
    }

    class MockResponse:
        status = 200
        async def json(self, content_type=None):
            return mock_payload
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass

    class MockSession:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        def get(self, url):
            return MockResponse()

    monkeypatch.setattr("aiohttp.ClientSession", MockSession)

    raw_res = await get_weather("Минск", lang="ru")
    data = json.loads(raw_res)

    assert data["city"] == "Минск"
    assert data["temp"] == 14.0
    assert data["description"] == "Ясно"
    assert data["humidity"] == 65
    assert data["wind_speed"] == 5.0
    assert data["pressure"] == 1015
    assert data["requires_city_selection"] is False


@pytest.mark.asyncio
async def test_api_weather_endpoint_with_none_city():
    # 1. /api/weather/none in Russian
    resp_ru = await get_weather_endpoint(city="none", lang="ru")
    assert resp_ru.temp is None
    assert "Сначала выберите город" in resp_ru.description

    # 2. /api/weather/none in Belarusian
    resp_by = await get_weather_endpoint(city="none", lang="by")
    assert resp_by.temp is None
    assert "Спачатку выберыце горад" in resp_by.description

    # 3. /api/weather/null
    resp_null = await get_weather_endpoint(city="null", lang="by")
    assert resp_null.temp is None
    assert "Спачатку выберыце горад" in resp_null.description

    # 4. /api/weather (city is None)
    resp_none = await get_weather_endpoint(city=None, lang="ru")
    assert resp_none.temp is None
    assert "Сначала выберите город" in resp_none.description
