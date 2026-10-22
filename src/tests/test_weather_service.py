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
    WeatherDTO,
    WeatherDaySummary,
    WeatherHourlyItem,
    extract_description,
    format_hourly_time,
    format_time_12_to_24,
    get_city_selection_reminder,
    get_weather,
    is_city_missing,
)
from src.routers.api_integrated import get_weather_endpoint

def test_is_city_missing_detection():
    assert is_city_missing(None) is True
    assert is_city_missing("") is True
    assert is_city_missing("   ") is True

    assert is_city_missing("none") is True
    assert is_city_missing("None") is True
    assert is_city_missing("NONE") is True
    assert is_city_missing("null") is True
    assert is_city_missing("Null") is True
    assert is_city_missing("undefined") is True
    assert is_city_missing("0") is True

    assert is_city_missing("Минск") is False
    assert is_city_missing("Брест") is False
    assert is_city_missing("Grodno") is False

def test_city_selection_reminder_translations():
    reminder_ru = get_city_selection_reminder("ru")
    assert "Сначала выберите город" in reminder_ru
    assert "Путешествия" in reminder_ru

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
    resp_ru = await get_weather_endpoint(city="none", lang="ru")
    assert resp_ru.temp is None
    assert "Сначала выберите город" in resp_ru.description

    resp_by = await get_weather_endpoint(city="none", lang="by")
    assert resp_by.temp is None
    assert "Спачатку выберыце горад" in resp_by.description

    resp_null = await get_weather_endpoint(city="null", lang="by")
    assert resp_null.temp is None
    assert "Спачатку выберыце горад" in resp_null.description

    resp_none = await get_weather_endpoint(city=None, lang="ru")
    assert resp_none.temp is None
    assert "Сначала выберите город" in resp_none.description

def test_time_conversion_utilities():
    assert format_hourly_time("0") == "00:00"
    assert format_hourly_time(0) == "00:00"
    assert format_hourly_time("300") == "03:00"
    assert format_hourly_time("900") == "09:00"
    assert format_hourly_time("1200") == "12:00"
    assert format_hourly_time("1800") == "18:00"
    assert format_hourly_time("2100") == "21:00"
    assert format_hourly_time("") == ""
    assert format_hourly_time(None) == ""

    assert format_time_12_to_24("07:34 AM") == "07:34"
    assert format_time_12_to_24("06:20 PM") == "18:20"
    assert format_time_12_to_24("12:00 AM") == "00:00"
    assert format_time_12_to_24("12:15 PM") == "12:15"
    assert format_time_12_to_24(None) is None
    assert format_time_12_to_24("invalid") == "invalid"

def test_extract_description_fallbacks():
    assert extract_description({"lang_be": [{"value": "Хмарна"}], "weatherDesc": [{"value": "Cloudy"}]}) == "Хмарна"
    assert extract_description({"weatherDesc": [{"value": "Sunny"}]}) == "Sunny"
    assert extract_description({"lang_xx": [{"value": "Ясна"}]}) == "Ясна"
    assert extract_description({}) == ""

@pytest.mark.asyncio
async def test_get_weather_extended_payload(monkeypatch):
    mock_payload = {
        "current_condition": [
            {
                "temp_C": "14",
                "FeelsLikeC": "11",
                "uvIndex": "3",
                "visibility": "10",
                "weatherDesc": [{"value": "Overcast"}],
                "lang_be": [{"value": "Хмарна"}],
                "humidity": "70",
                "windspeedKmph": "18",
                "pressure": "1016",
            }
        ],
        "weather": [
            {
                "date": "2026-10-12",
                "maxtempC": "15",
                "mintempC": "8",
                "astronomy": [
                    {
                        "sunrise": "07:34 AM",
                        "sunset": "06:20 PM",
                    }
                ],
                "hourly": [
                    {
                        "time": "0",
                        "tempC": "9",
                        "chanceofrain": "40",
                        "lang_be": [{"value": "Невялікі дождж"}],
                    },
                    {
                        "time": "300",
                        "tempC": "8",
                        "chanceofrain": 10,
                        "weatherDesc": [{"value": "Clear"}],
                    },
                ],
            },
            {
                "date": "2026-10-13",
                "maxtempC": "16",
                "mintempC": "7",
            },
            {
                "date": "2026-10-14",
                "maxtempC": "14",
                "mintempC": "6",
            },
        ],
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

    raw_res = await get_weather("Гродна", lang="be")
    data = json.loads(raw_res)

    dto = WeatherDTO(**data)
    assert dto.city == "Гродна"
    assert dto.temp == 14.0
    assert dto.feels_like == 11.0
    assert dto.uv_index == 3.0
    assert dto.visibility == 10.0
    assert dto.description == "Хмарна"
    assert dto.sunrise == "07:34"
    assert dto.sunset == "18:20"
    assert len(dto.hourly) == 2
    assert dto.hourly[0].time == "00:00"
    assert dto.hourly[0].temp == 9.0
    assert dto.hourly[0].chance_of_rain == 40
    assert dto.hourly[0].description == "Невялікі дождж"
    assert dto.hourly[1].time == "03:00"
    assert dto.hourly[1].temp == 8.0
    assert dto.hourly[1].chance_of_rain == 10
    assert dto.hourly[1].description == "Clear"
    assert len(dto.forecast) == 3
    assert dto.forecast[0].date == "2026-10-12"
    assert dto.forecast[0].max_temp == 15.0
    assert dto.forecast[0].min_temp == 8.0

@pytest.mark.asyncio
async def test_endpoint_returns_extended_dto(monkeypatch):
    mock_payload = {
        "current_condition": [
            {
                "temp_C": "12",
                "FeelsLikeC": "10",
                "weatherDesc": [{"value": "Cloudy"}],
                "humidity": "60",
                "windspeedKmph": "10",
                "pressure": "1012",
            }
        ],
        "weather": [
            {
                "date": "2026-10-12",
                "maxtempC": "13",
                "mintempC": "7",
                "astronomy": [{"sunrise": "07:30 AM", "sunset": "06:15 PM"}],
                "hourly": [{"time": "600", "tempC": "9", "chanceofrain": "5", "weatherDesc": [{"value": "Cloudy"}]}],
            }
        ],
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
    monkeypatch.setattr("src.routers.api_integrated.check_weather_cache", AsyncMock(return_value=None))
    monkeypatch.setattr("src.routers.api_integrated.set_weather_cache", AsyncMock(return_value=None))

    res = await get_weather_endpoint(city="Брест", lang="be")
    assert res.city == "Брест"
    assert res.temp == 12.0
    assert res.feels_like == 10.0
    assert res.sunrise == "07:30"
    assert res.sunset == "18:15"
    assert len(res.hourly) == 1
    assert res.hourly[0].time == "06:00"
    assert res.hourly[0].temp == 9.0

@pytest.mark.asyncio
async def test_get_weather_formats_lang_dynamically(monkeypatch):
    called_urls = []

    class MockResponse:
        status = 200
        async def json(self, content_type=None):
            return {
                "current_condition": [
                    {
                        "temp_C": "15",
                        "weatherDesc": [{"value": "Солнечно"}],
                        "humidity": "60",
                        "windspeedKmph": "10",
                        "pressure": "1012",
                    }
                ]
            }
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
            called_urls.append(url)
            return MockResponse()

    monkeypatch.setattr("aiohttp.ClientSession", MockSession)

    await get_weather("Гродно", lang="ru")
    assert "lang=ru" in called_urls[-1]

    await get_weather("Гродно", lang="by")
    assert "lang=be" in called_urls[-1]

    await get_weather("Гродно", lang="en")
    assert "lang=en" in called_urls[-1]
