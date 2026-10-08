"""Test suite for the updated Wikimedia image fetching pipeline.

Verifies:
1. Softened file validation: non-Latin filenames, portraits, and paintings/exhibits
   are accepted or categorized as secondary fallbacks; maps/flags/SVGs are rejected.
2. Cascading query normalizer: strips quotes, initials, noise words, country tokens,
   and generates clean language-consistent variants.
3. OSM tags and Wikidata Q-ID property P18 (image) resolution for osm:node:2788680456.
4. Live photo resolution for Belarusian locations across multiple regions.
"""

import pytest
from src.utils.wiki_filters import (
    clean_place_name,
    extract_core_keywords,
    generate_cascading_queries,
    generate_category_search_queries,
    is_secondary_visual,
    is_valid_photo,
    match_score,
)
from src.services.wiki_service import (
    _parse_osm_id,
    get_wikimedia_photo,
)


# ===========================================================================
# 1. Validation Logic & Fallback Audit
# ===========================================================================

def test_validation_accepts_non_latin_filenames():
    info = {
        "url": "https://upload.wikimedia.org/wikipedia/commons/b/ba/Магілёў.jpg",
        "extmetadata": {},
    }
    assert is_valid_photo(info, title="File:Магілёў, былы пазямельна-сялянскі банк.jpg") is True


def test_validation_accepts_photos_without_size_metadata():
    info = {
        "url": "https://upload.wikimedia.org/wikipedia/commons/1/1a/sample.jpg",
        "width": 0,
        "height": 0,
    }
    assert is_valid_photo(info, title="File:sample.jpg") is True


def test_validation_accepts_portrait_orientations():
    info = {
        "url": "https://upload.wikimedia.org/wikipedia/commons/1/1a/portrait.jpg",
        "width": 400,
        "height": 600,
    }
    assert is_valid_photo(info, title="File:portrait.jpg") is True


def test_validation_accepts_paintings_and_exhibits_as_valid_visuals():
    info = {
        "url": "https://upload.wikimedia.org/wikipedia/commons/5/56/paint.jpg",
        "width": 1200,
        "height": 800,
        "extmetadata": {
            "ImageDescription": {
                "value": "Уладзімір Кудрэвіч. Восеньскі матыў. 1955 : кардон пастэль. Магілёўскі абласны мастацкі музей імя П. В. Масленікава."
            }
        },
    }
    # Must NOT be rejected as invalid
    assert is_valid_photo(info, title="File:Уладзімір Кудрэвіч. Восеньскі матыў.jpg") is True
    # Must be categorized as a secondary visual (fallback)
    assert is_secondary_visual(info, title="File:Уладзімір Кудрэвіч. Восеньскі матыў.jpg") is True


def test_validation_rejects_svg_and_non_image_extensions():
    for ext in (".svg", ".pdf", ".djvu", ".tif", ".tiff", ".webm", ".ogv"):
        info = {"url": f"https://upload.wikimedia.org/test{ext}"}
        assert is_valid_photo(info, title=f"File:test{ext}") is False


def test_validation_rejects_maps_flags_and_coats_of_arms():
    bad_assets = [
        ({"url": "https://upload.wikimedia.org/map.jpg"}, "File:Locator_map_of_Mogilev.jpg"),
        ({"url": "https://upload.wikimedia.org/arms.jpg"}, "File:Coat_of_arms_of_Belarus.jpg"),
        ({"url": "https://upload.wikimedia.org/flag.jpg"}, "File:Flag_of_Minsk.jpg"),
        (
            {
                "url": "https://upload.wikimedia.org/desc_map.jpg",
                "extmetadata": {"ImageDescription": {"value": "Location map showing Belarus"}},
            },
            "File:belarus_view.jpg",
        ),
    ]
    for info, title in bad_assets:
        assert is_valid_photo(info, title=title) is False, f"Failed to reject: {title}"


def test_secondary_visual_distinguishes_building_from_artifacts():
    building_info = {
        "url": "https://upload.wikimedia.org/building.jpg",
        "extmetadata": {
            "ObjectName": {"value": "Магілёў, былы пазямельна-сялянскі банк, foto by futureal"},
            "Categories": {"value": "Building of Peasant Land Bank, Mahilioŭ|Cultural heritage monuments"},
        },
    }
    assert is_secondary_visual(building_info, title="File:Магілёў, былы пазямельна-сялянскі банк.jpg") is False

    icon_info = {
        "url": "https://upload.wikimedia.org/icon.jpg",
        "extmetadata": {
            "ObjectName": {"value": "Белыничская икона Божией Матери"},
            "Categories": {"value": "Icons in Mahilioŭ Regional Museum of Art"},
        },
    }
    assert is_secondary_visual(icon_info, title="File:Белыничская икона Божией Матери1.jpg") is True


def test_match_score_with_metadata_fallback():
    # An exhibit whose filename does not match the museum name, but whose description explicitly mentions it
    score = match_score(
        title="File:Уладзімір Кудрэвіч. Восеньскі матыў.jpg",
        name="Магілёўскі абласны мастацкі музей імя П. В. Масленікава",
        city="Могилев",
        metadata={
            "ImageDescription": {
                "value": "Магілёўскі абласны мастацкі музей імя П. В. Масленікава. Жывапіс."
            }
        },
    )
    assert score >= 45


# ===========================================================================
# 2. Cascading Query Normalizer
# ===========================================================================

def test_clean_place_name_strips_punctuation_initials_and_noise():
    raw_name = '"Магілёўскі абласны мастацкі музей імя П. В. Масленікава" Belarus'
    cleaned = clean_place_name(raw_name)
    assert "П. В." not in cleaned
    assert "імя" not in cleaned
    assert "абласны" not in cleaned
    assert "Belarus" not in cleaned
    assert '"' not in cleaned
    assert "Масленікава" in cleaned


def test_extract_core_keywords():
    name = "Магілёўскі абласны мастацкі музей імя П. В. Масленікава"
    type_word, proper_name = extract_core_keywords(name)
    assert type_word == "музей"
    assert proper_name == "Масленікава"


def test_generate_cascading_queries_variants():
    queries = generate_cascading_queries(
        name='"Магілёўскі абласны мастацкі музей імя П. В. Масленікава" Belarus',
        city="Могилев",
    )
    assert any("Масленікава" in q and "Магілёў" in q for q in queries)
    assert any("Масленикова" in q for q in queries)
    # Ensure no verbatim quotes or initials leaked into any variant
    for q in queries:
        assert '"' not in q
        assert "П. В." not in q
        assert "імя" not in q.split()


def test_generate_category_search_queries():
    cat_queries = generate_category_search_queries(
        name="Магілёўскі абласны мастацкі музей імя П. В. Масленікава",
        city="Могилев",
    )
    assert any("Масленикова" in q or "Масленікава" in q for q in cat_queries)


# ===========================================================================
# 3. OSM & Wikidata Parsing
# ===========================================================================

def test_parse_osm_id():
    assert _parse_osm_id("osm:node:2788680456") == ("node", 2788680456)
    assert _parse_osm_id("osm:way:123456") == ("way", 123456)
    assert _parse_osm_id("osm:relation:999") == ("relation", 999)
    assert _parse_osm_id("node:2788680456") == ("node", 2788680456)
    assert _parse_osm_id("osm:hash123456") == (None, None)


# ===========================================================================
# 4. End-to-End Resolution for Belarusian Locations
# ===========================================================================

@pytest.mark.asyncio
async def test_resolve_maslenikov_museum_via_osm_node():
    """Verify that osm:node:2788680456 resolves via OSM and Wikidata P18 image."""
    photo = await get_wikimedia_photo(
        name='"Магілёўскі абласны мастацкі музей імя П. В. Масленікава" Belarus',
        city="Могилев",
        place_id="osm:node:2788680456",
        lat=53.9080713,
        lon=30.3385922,
        category="museum",
    )
    assert photo is not None
    assert photo.get("source") == "wikimedia"
    assert "upload.wikimedia.org" in photo.get("original_url", "")
    assert photo.get("local_url_thumb", "").endswith(".webp")
    assert photo.get("local_url_medium", "").endswith(".webp")


@pytest.mark.asyncio
async def test_resolve_brest_fortress():
    """Verify resolution of Brest Fortress via clean cascading search."""
    photo = await get_wikimedia_photo(
        name="Брэсцкая крэпасць-герой",
        city="Брест",
        place_id="test:brest:001",
        lat=52.0833,
        lon=23.6583,
        category="memorial",
    )
    assert photo is not None
    assert "upload.wikimedia.org" in photo.get("original_url", "")


@pytest.mark.asyncio
async def test_resolve_mir_castle():
    """Verify resolution of Mir Castle."""
    photo = await get_wikimedia_photo(
        name="Мірскі замак",
        city="Мир",
        place_id="test:mir:002",
        lat=53.4514,
        lon=26.4731,
        category="castle",
    )
    assert photo is not None
    assert "upload.wikimedia.org" in photo.get("original_url", "")


# ===========================================================================
# 5. Frontend & Proxy Verification
# ===========================================================================

@pytest.mark.asyncio
async def test_photo_proxy_exempt_from_auth():
    """Verify that /api/geo/photo-proxy is exempt from TelegramAuthMiddleware."""
    from fastapi import FastAPI
    from src.middleware.telegram_auth import TelegramAuthMiddleware

    app = FastAPI()
    app.add_middleware(TelegramAuthMiddleware, bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")

    @app.get("/api/geo/photo-proxy")
    async def proxy():
        return {"status": "ok"}

    @app.get("/api/pois/secret")
    async def secret():
        return {"status": "secret"}

    async def call_asgi(path):
        status = None
        async def send(msg):
            nonlocal status
            if msg["type"] == "http.response.start":
                status = msg["status"]
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": [],
            "state": {},
        }
        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}
        await app(scope, receive, send)
        return status

    assert await call_asgi("/api/geo/photo-proxy") == 200
    assert await call_asgi("/api/pois/secret") == 401


@pytest.mark.asyncio
async def test_wikimedia_photo_endpoint_resolution():
    """Verify that /api/geo/pois/{id}/wikimedia-photo router endpoint resolves and caches photos."""
    from src.routers.wikimedia_photos import wikimedia_photo

    res = await wikimedia_photo("osm:node:2788680456")
    assert res is not None
    assert "photo" in res
    photo = res["photo"]
    assert photo is not None
    assert "upload.wikimedia.org" in photo.get("original_url", "")
    assert photo.get("thumbnail_url", "").startswith("https://") or photo.get("thumbnail_url", "").startswith("/media/")
