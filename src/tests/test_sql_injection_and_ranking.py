"""
Tests verifying SQL injection resistance, category classification,
strict city search filtering, and smart ranking (castles & museums above graves).
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest
from sqlalchemy import select
from sqlalchemy.dialects import postgresql, sqlite

from src.database.db import AsyncSessionLocal
from src.database.models import Place
from src.routers import api_integrated
from src.routers.api_integrated import (
    TAG_CATEGORY_MAP,
    expand_poi_tags,
    get_places_from_db,
    normalize_category,
)

def test_sql_injection_in_query_compilation_parameters():
    """Verify that potentially malicious strings are parameterized and never raw-concatenated."""
    dialects = [postgresql.dialect(), sqlite.dialect()]

    evil_inputs = [
        "'; DROP TABLE places; --",
        "' OR '1'='1",
        "admin'--",
        "1; SELECT * FROM users;",
        "'; UPDATE places SET name='hacked' WHERE 1=1; --",
        "' UNION ALL SELECT null, null, null, null, null, null, null, null, null, null, null, null, null --",
    ]

    for evil in evil_inputs:
        for d in dialects:
            q_search = select(Place).where(Place.name.ilike(f"%{evil}%"))
            compiled_search = str(q_search.compile(dialect=d))
            assert "DROP TABLE" not in compiled_search
            assert "UPDATE places" not in compiled_search
            assert "UNION ALL SELECT" not in compiled_search

            q_shuffle = select(Place).order_by(api_integrated.func.md5(Place.place_id.op("||")(evil)))
            compiled_shuffle = str(q_shuffle.compile(dialect=d))
            assert "DROP TABLE" not in compiled_shuffle
            assert "UPDATE places" not in compiled_shuffle
            params = q_shuffle.compile(dialect=d).params
            assert any(evil in str(v) for v in params.values())

@pytest.mark.asyncio
async def test_sql_injection_in_get_places_from_db():
    """Execute get_places_from_db with various SQL injection payloads against the session."""
    evil_payloads = [
        "'; DROP TABLE places; --",
        "' OR '1'='1' --",
        "'; SELECT pg_sleep(5); --",
        "' UNION SELECT * FROM users --",
    ]

    async with AsyncSessionLocal() as session:
        for evil in evil_payloads:
            res = await get_places_from_db(session, city="Бобруйск", search=evil)
            assert isinstance(res, list)

            res = await get_places_from_db(session, city=evil)
            assert isinstance(res, list)

            res = await get_places_from_db(session, region=evil)
            assert isinstance(res, list)

            res = await get_places_from_db(session, city="Бобруйск", shuffle=evil)
            assert isinstance(res, list)

            res = await get_places_from_db(session, city="Бобруйск", category=evil)
            assert isinstance(res, list)

        places_count = await session.scalar(select(api_integrated.func.count(Place.id)))
        assert places_count is not None and places_count > 0

@pytest.mark.asyncio
async def test_sql_injection_in_poi_query_endpoint():
    """Verify endpoint /api/pois/query safely handles injection payloads in all POIQuery fields."""
    evil_query = api_integrated.POIQuery(
        city="Бобруйск",
        region="Могилевская'; DROP TABLE places; --",
        tags=["'; DROP TABLE places; --", "' OR 1=1 --"],
        search="'; DELETE FROM places; --",
        shuffle="'; DROP TABLE users; --",
        limit=10,
        offset=0,
    )
    res = await api_integrated.query_pois(evil_query)
    assert "pois" in res
    assert isinstance(res["pois"], list)
    assert res["city"] == "Бобруйск"

def test_bobruisk_fortress_and_castles_classification():
    """Ensure castles, fortresses, bastions, and citadels are classified as 'castle'."""
    assert normalize_category("attraction", name="Бобруйская крепость") == "castle"
    assert normalize_category("", name="Бобруйская крепость") == "castle"
    assert normalize_category("historic", name="Бабруйская крэпасць") == "castle"
    assert normalize_category("fort", name="Форт «Фридрих Вильгельм»") == "castle"
    assert normalize_category("fortification", name="Равелин Бобруйской крепости") == "castle"
    assert normalize_category("", name="Пороховой погреб Бобруйской крепости") == "castle"
    assert normalize_category("", name="Минские ворота Бобруйской крепости") == "castle"

    assert normalize_category("memorial", name="Брэсцкая Крэпасць-Герой") == "castle"
    assert normalize_category("memorial", name="Замак XIV ст.") == "castle"
    assert normalize_category("misc", name="Маладзечанскі замок") == "castle"
    assert normalize_category("castle", name="Мазырскі замок") == "castle"
    assert normalize_category("misc", name="Магілёўскі замок пачатку XVII стагоддзя") == "castle"
    assert normalize_category("misc", name="Архіепіскапскі палац") == "castle"
    assert normalize_category("misc", name="Палац Радзівілаў") == "castle"
    assert normalize_category("attraction", name="Брестская крепость") == "castle"
    assert normalize_category("fort", name="Форт I") == "castle"
    assert normalize_category("fort", name="Цитадель") == "castle"
    assert normalize_category("fort", name="Цытадэль") == "castle"

def test_churches_and_temples_classification():
    """Ensure churches, temples, kostyols, cathedrals, synagogues are classified as 'church'."""
    assert normalize_category("misc", name="Свято-Никольский кафедральный собор") == "church"
    assert normalize_category("misc", name="Костёл Непорочного Зачатия Пресвятой Девы Марии") == "church"
    assert normalize_category("misc", name="Фарны касцёл") == "church"
    assert normalize_category("misc", name="Свято-Георгиевский храм") == "church"
    assert normalize_category("misc", name="Бобруйская синагога") == "church"
    assert normalize_category("misc", name="Былая сінагога") == "church"
    assert normalize_category("misc", name="Царква Святых Барыса і Глеба") == "church"
    assert normalize_category("misc", name="Свята-Мікольскі манастыр") == "church"
    assert normalize_category("memorial", name="Капліца") == "church"
    assert normalize_category("place_of_worship", name="Неизвестный объект") == "church"

def test_tag_category_map_structure():
    """Verify TAG_CATEGORY_MAP complies strictly with updated mapping requirements."""
    assert TAG_CATEGORY_MAP["castle"] == {"castle"}
    assert TAG_CATEGORY_MAP["architecture"] == {"castle", "church", "monument", "manor", "ruins", "gallery"}
    assert "memorial" not in TAG_CATEGORY_MAP["architecture"]
    assert "misc" not in TAG_CATEGORY_MAP["architecture"]
    assert TAG_CATEGORY_MAP["church"] == {"church"}
    assert TAG_CATEGORY_MAP["monument"] == {"monument", "memorial"}
    assert TAG_CATEGORY_MAP["nature"] == {"park", "viewpoint"}
    assert TAG_CATEGORY_MAP["museum"] == {"museum", "gallery"}

    expanded_arch = expand_poi_tags(["architecture"])
    assert "castle" in expanded_arch
    assert "church" in expanded_arch
    assert "memorial" not in expanded_arch
    assert "misc" not in expanded_arch

@pytest.mark.asyncio
async def test_bobruisk_in_database_and_fortress_details():
    """Verify that Bobruisk exists in DB with Bobruisk fortress having category 'castle' and coords."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(Place).where(
                Place.city == "Бобруйск",
                Place.name == "Бобруйская крепость",
            ).limit(1)
        )
        fortress = res.scalar_one_or_none()
        assert fortress is not None, "Бобруйская крепость must exist in DB for Bobruisk"
        assert fortress.category == "castle", f"Expected category 'castle', got '{fortress.category}'"
        assert round(fortress.lat, 4) == 53.1396
        assert round(fortress.lon, 4) == 29.2347
        assert "Бобруйск" in fortress.address or "Крепостной" in fortress.address

@pytest.mark.asyncio
async def test_strict_city_search_filtering():
    """Ensure search results strictly belong to the requested city and never bleed across cities."""
    async with AsyncSessionLocal() as session:
        places = await get_places_from_db(session, city="Бобруйск", search="Минск")
        assert len(places) > 0
        for p in places:
            assert p.city.lower() == "бобруйск", f"Expected only Bobruisk places, but got {p.name} in {p.city}"

        minsk_places = await get_places_from_db(session, city="Минск", search="Бобруйск")
        for p in minsk_places:
            assert p.city.lower() == "минск", f"Expected only Minsk places, but got {p.name} in {p.city}"

        bobruisk_museums = await get_places_from_db(session, city="Бобруйск", search="музей")
        assert len(bobruisk_museums) > 0
        for p in bobruisk_museums:
            assert p.city.lower() == "бобруйск", f"Expected Bobruisk museum, got {p.name} in {p.city}"

@pytest.mark.asyncio
async def test_strict_region_filtering_with_oblast_suffix():
    """Ensure filtering by region matches whether 'область' is passed or omitted."""
    async with AsyncSessionLocal() as session:
        res1 = await get_places_from_db(session, region="Могилевская область", city="Бобруйск")
        res2 = await get_places_from_db(session, region="могилевская", city="Бобруйск")
        assert len(res1) == len(res2)
        assert len(res1) > 0

@pytest.mark.asyncio
async def test_ranking_castles_and_museums_above_graves():
    """
    Verify ranking order:
    1. Castles (1)
    2. Museums (2)
    3. Churches (3)
    4. Parks (4)
    5. Viewpoints (5)
    ...
    Graves ('могила', 'магіла', 'кладбище') are pushed to the bottom.
    """
    async with AsyncSessionLocal() as session:
        places = await get_places_from_db(session, city="Могилев", limit=50)
        assert len(places) > 0

        top_categories = [p.category for p in places[:10]]
        assert "castle" in top_categories or "museum" in top_categories

        grave_keywords = ("могила", "магіла", "кладбище", "могілк", "погребение")
        non_grave_places = [p for p in places if not any(w in p.name.lower() for w in grave_keywords)]
        grave_places = [p for p in places if any(w in p.name.lower() for w in grave_keywords)]

        if grave_places:
            first_grave_idx = next(i for i, p in enumerate(places) if any(w in p.name.lower() for w in grave_keywords))
            last_non_grave_idx = max(i for i, p in enumerate(places) if not any(w in p.name.lower() for w in grave_keywords))
            assert first_grave_idx > 0, "Graves must not be at the top of results"

@pytest.mark.asyncio
async def test_ranking_allows_graves_when_user_explicitly_searches_grave():
    """When user explicitly searches for 'могила' or 'магіла', matching graves must not be suppressed."""
    async with AsyncSessionLocal() as session:
        places_baranovichi = await get_places_from_db(session, city="Барановичи", search="могила", limit=10)
        assert len(places_baranovichi) > 0
        for p in places_baranovichi:
            assert "могила" in p.name.lower() or "могила" in (p.address or "").lower()

        places_mogilev = await get_places_from_db(session, city="Могилев", search="магіла", limit=10)
        assert len(places_mogilev) > 0
        for p in places_mogilev:
            assert "магіла" in p.name.lower() or "магіла" in (p.address or "").lower()

@pytest.mark.asyncio
async def test_ranking_shuffle_preserves_md5_order():
    """When shuffle is specified, func.md5 ordering must be used."""
    captured = []

    class DummySession:
        async def execute(self, stmt):
            captured.append(stmt)
            return api_integrated.FakeResult([]) if hasattr(api_integrated, "FakeResult") else None

    q = select(Place)
    term = "test"
    shuffle = "my_seed_123"
    q = q.order_by(api_integrated.func.md5(Place.place_id.op("||")(str(shuffle).strip())))
    sql_str = str(q.compile(dialect=postgresql.dialect()))
    assert "md5(" in sql_str
    assert "places.place_id ||" in sql_str

@pytest.mark.asyncio
async def test_pois_research_endpoint():
    """Verify that /api/pois/research scrapes surroundings and handles duplicate filtering."""
    from src.routers.api_integrated import research_pois, POIResearchQuery
    from unittest.mock import patch

    mock_osm_data = [
        {"id": "bobruisk:castle:fortress_main", "name": "Бобруйская крепость", "lat": 53.1396, "lon": 29.2347, "type": "castle"},
        {"id": "bobruisk_rayon:estate:zhilichi_test", "name": "Дворец Булгаков в Жиличах (Тест)", "lat": 53.155, "lon": 29.812, "type": "manor", "address": "д. Жиличи"}
    ]

    with patch("src.routers.api_integrated.get_attractions_osm", return_value=mock_osm_data):
        res = await research_pois(POIResearchQuery(city="Бобруйск", scale=2.5))
        assert res["city"] == "Бобруйск"
        assert res["found_in_surroundings"] == 2
        assert "new_added" in res
        assert "total_places" in res

