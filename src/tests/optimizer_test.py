from src.services.optimizer_service import optimizeRoutePoints


def test_optimize_empty_list():
    result = optimizeRoutePoints([])

    assert result == []


def test_optimize_single_point():
    points = [
        {
            "id": "p1",
            "name": "Точка 1",
            "lat": 53.9000,
            "lon": 27.5600,
        }
    ]

    result = optimizeRoutePoints(points)

    assert len(result) == 1
    assert result[0]["id"] == "p1"


def test_optimize_two_points():
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
            "lat": 53.9300,
            "lon": 27.6500,
        },
    ]

    result = optimizeRoutePoints(points)

    assert len(result) == 2
    assert result[0]["id"] == "p1"
    assert result[1]["id"] == "p2"


def test_optimize_removes_invalid_points():
    points = [
        {
            "id": "p1",
            "name": "Точка 1",
            "lat": 53.9000,
            "lon": 27.5600,
        },
        {
            "id": "invalid1",
            "name": "Без координат",
        },
        {
            "id": "invalid2",
            "name": "Неверная широта",
            "lat": "abc",
            "lon": 27.5800,
        },
        {
            "id": "p2",
            "name": "Точка 2",
            "lat": 53.9300,
            "lon": 27.6500,
        },
    ]

    result = optimizeRoutePoints(points)

    assert len(result) == 2
    assert [point["id"] for point in result] == ["p1", "p2"]


def test_optimize_removes_duplicate_coordinates():
    points = [
        {
            "id": "p1",
            "name": "Точка 1",
            "lat": 53.900000,
            "lon": 27.560000,
        },
        {
            "id": "p1_duplicate",
            "name": "Дубликат",
            "lat": 53.900000,
            "lon": 27.560000,
        },
        {
            "id": "p2",
            "name": "Точка 2",
            "lat": 53.930000,
            "lon": 27.650000,
        },
    ]

    result = optimizeRoutePoints(points)

    assert len(result) == 2
    assert [point["id"] for point in result] == ["p1", "p2"]


def test_optimize_keeps_all_valid_points():
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
            "lat": 53.9500,
            "lon": 27.7000,
        },
        {
            "id": "p3",
            "name": "Точка 3",
            "lat": 53.9100,
            "lon": 27.5700,
        },
        {
            "id": "p4",
            "name": "Точка 4",
            "lat": 53.9200,
            "lon": 27.6000,
        },
    ]

    result = optimizeRoutePoints(points)

    assert len(result) == 4
    assert {point["id"] for point in result} == {
        "p1",
        "p2",
        "p3",
        "p4",
    }


def test_optimize_preserves_first_point():
    points = [
        {
            "id": "start",
            "name": "Старт",
            "lat": 53.9000,
            "lon": 27.5600,
        },
        {
            "id": "far",
            "name": "Далеко",
            "lat": 54.1000,
            "lon": 28.0000,
        },
        {
            "id": "near",
            "name": "Рядом",
            "lat": 53.9050,
            "lon": 27.5650,
        },
    ]

    result = optimizeRoutePoints(points)

    assert result[0]["id"] == "start"


def test_optimize_nearest_neighbor_order():
    points = [
        {
            "id": "start",
            "name": "Старт",
            "lat": 53.9000,
            "lon": 27.5600,
        },
        {
            "id": "near",
            "name": "Рядом",
            "lat": 53.9010,
            "lon": 27.5610,
        },
        {
            "id": "far",
            "name": "Далеко",
            "lat": 54.1000,
            "lon": 28.0000,
        },
    ]

    result = optimizeRoutePoints(points)

    assert result[0]["id"] == "start"
    assert result[1]["id"] == "near"
    assert result[2]["id"] == "far"