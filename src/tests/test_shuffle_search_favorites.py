import pytest
from types import SimpleNamespace
from sqlalchemy import select
from src.routers import api_integrated
from src.database.models import Place, Favorite, User


class FakeScalars:
    def __init__(self, items):
        self.items = items

    def all(self):
        return self.items

    def scalar_one_or_none(self):
        return self.items[0] if self.items else None


class FakeResult:
    def __init__(self, items):
        self.items = items

    def scalars(self):
        return FakeScalars(self.items)

    def scalar_one_or_none(self):
        return self.items[0] if self.items else None


@pytest.mark.asyncio
async def test_poi_query_schema_and_defaults():
    q = api_integrated.POIQuery(region="Минская область", city="Минск")
    assert q.search is None
    assert q.shuffle is None
    assert q.limit == 30
    assert q.offset == 0

    q_search = api_integrated.POIQuery(region="Минская область", search="замок", shuffle="seed123")
    assert q_search.search == "замок"
    assert q_search.shuffle == "seed123"


@pytest.mark.asyncio
async def test_favorites_pagination_endpoint(monkeypatch):
    favs = [
        SimpleNamespace(id=1, user_id=123, place_id="p1", place_name="Place 1", address="Addr 1", lat=53.9, lon=27.5),
        SimpleNamespace(id=2, user_id=123, place_id="p2", place_name="Place 2", address="Addr 2", lat=53.91, lon=27.51),
        SimpleNamespace(id=3, user_id=123, place_id="p3", place_name="Place 3", address="Addr 3", lat=53.92, lon=27.52),
    ]

    class FakeFavSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        async def execute(self, stmt):
            stmt_str = str(stmt).lower()
            if "count" in stmt_str:
                return FakeResult([len(favs)])
            # Check for limit / offset
            offset = getattr(stmt, "_offset", 0) or 0
            limit = getattr(stmt, "_limit", None)
            if limit is not None:
                return FakeResult(favs[offset : offset + limit])
            return FakeResult(favs)

    monkeypatch.setattr(api_integrated, "AsyncSessionLocal", lambda: FakeFavSession())

    class FakeRequest:
        state = SimpleNamespace(telegram_user_id=123)

    # 1. Unpaginated request (backward compatibility)
    res_all = await api_integrated.get_favorites(FakeRequest())
    assert len(res_all["favorites"]) == 3
    assert res_all["total"] == 3
    assert res_all["has_next"] is False

    # 2. Paginated request: page 0, size 2
    res_p0 = await api_integrated.get_favorites(FakeRequest(), page=0, page_size=2)
    assert len(res_p0["favorites"]) == 2
    assert res_p0["total"] == 3
    assert res_p0["page"] == 0
    assert res_p0["pages"] == 2
    assert res_p0["has_next"] is True

    # 3. Paginated request: page 1, size 2
    res_p1 = await api_integrated.get_favorites(FakeRequest(), page=1, page_size=2)
    assert len(res_p1["favorites"]) == 1
    assert res_p1["page"] == 1
    assert res_p1["has_next"] is False


@pytest.mark.asyncio
async def test_query_pois_with_search_and_shuffle(monkeypatch):
    captured_queries = []

    class FakePOISession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        async def execute(self, stmt):
            captured_queries.append(stmt)
            if "place_photos" in str(stmt).lower():
                return FakeResult([])
            p = SimpleNamespace(
                place_id="p10",
                name="Тестовый музей",
                city="Минск",
                region="Минская область",
                address="ул. Ленина",
                category="museum",
                lat=53.9,
                lon=27.5,
                hours=None,
                phone=None,
            )
            return FakeResult([p])

        async def commit(self):
            pass

    monkeypatch.setattr(api_integrated, "AsyncSessionLocal", lambda: FakePOISession())

    q = api_integrated.POIQuery(
        region="Минская область",
        city="Минск",
        search="музей",
        shuffle="seed_abc",
        limit=10,
        offset=0,
    )
    res = await api_integrated.query_pois(q)

    assert res["count"] == 1
    assert res["search"] == "музей"
    assert res["shuffle"] == "seed_abc"
    assert len(res["pois"]) == 1
    assert res["pois"][0]["id"] == "p10"

    # Verify query captured by session
    assert len(captured_queries) >= 1
    sql_str = str(captured_queries[0])
    assert "places" in sql_str
    # Verify search clause was compiled
    assert "lower(places.name) LIKE lower(" in sql_str or "places.name LIKE" in sql_str or "places.address" in sql_str
    # Verify shuffle order clause was compiled
    assert "md5(" in sql_str

