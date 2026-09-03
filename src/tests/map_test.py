import pytest

from src.services.map_service import build_google_maps_link


def test_build_google_maps_link_two_points():
    points = [
        {
            "id": "p1",
            "name": "Минская площадь",
            "lat": 53.9000,
            "lon": 27.5600,
        },
        {
            "id": "p2",
            "name": "Национальная библиотека",
            "lat": 53.9300,
            "lon": 27.6500,
        },
    ]

    result = build_google_maps_link(points)

    assert result is not None
    assert result.startswith("https://www.google.com/maps/dir/?")
    assert "api=1" in result
    assert "origin=53.9%2C27.56" in result
    assert "destination=53.93%2C27.65" in result
    assert "waypoints=" not in result


def test_build_google_maps_link_with_waypoints():
    points = [
        {
            "id": "p1",
            "name": "Точка 1",
            "lat": 53.9000,
            "lon": 27.5600,
        },
        {
            "id": "p2",
            "name": "Точка 2",
            "lat": 53.9100,
            "lon": 27.5800,
        },
        {
            "id": "p3",
            "name": "Точка 3",
            "lat": 53.9300,
            "lon": 27.6500,
        },
    ]

    result = build_google_maps_link(points)

    assert result is not None
    assert "origin=53.9%2C27.56" in result
    assert "destination=53.93%2C27.65" in result
    assert "waypoints=" in result
    assert "53.91%2C27.58" in result


def test_build_google_maps_link_too_few_points():
    points = [
        {
            "id": "p1",
            "name": "Точка 1",
            "lat": 53.9000,
            "lon": 27.5600,
        }
    ]

    result = build_google_maps_link(points)

    assert result is None


def test_build_google_maps_link_empty_list():
    result = build_google_maps_link([])

    assert result is None