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
    assert is_valid_photo(info, title="File:Уладзімір Кудрэвіч. Восеньскі матыў.jpg") is True
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

def test_parse_osm_id():
    assert _parse_osm_id("osm:node:2788680456") == ("node", 2788680456)
    assert _parse_osm_id("osm:way:123456") == ("way", 123456)
    assert _parse_osm_id("osm:relation:999") == ("relation", 999)
    assert _parse_osm_id("node:2788680456") == ("node", 2788680456)
    assert _parse_osm_id("osm:hash123456") == (None, None)

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

def test_validation_rejects_bchb_and_protest_symbolism():
    """Verify rejection of BCHB, white-red-white flags, and protest symbols."""
    samples = [
        ({"url": "https://upload.wikimedia.org/bchb.jpg"}, "File:BCHB flag rally in Minsk.jpg"),
        ({"url": "https://upload.wikimedia.org/wrw.jpg"}, "File:White-red-white flag 2020.jpg"),
        (
            {
                "url": "https://upload.wikimedia.org/rally.jpg",
                "extmetadata": {"ImageDescription": {"value": "Бело-красно-белый флаг на митинге оппозиции"}},
            },
            "File:protest_minsk.jpg",
        ),
        (
            {
                "url": "https://upload.wikimedia.org/zhive.jpg",
                "extmetadata": {"Categories": {"value": "2020 Belarusian protests|Demonstrations"}},
            },
            "File:crowd.jpg",
        ),
        ({"url": "https://upload.wikimedia.org/slogan.jpg"}, "File:Zhive Belarus march.jpg"),
        ({"url": "https://upload.wikimedia.org/wrw_be.jpg"}, "File:Бел-чырвона-белы сцяг над плошчай.jpg"),
        ({"url": "https://upload.wikimedia.org/b_ch_b.jpg"}, "File:Б-ч-б сцягі на маршы.jpg"),
        ({"url": "https://upload.wikimedia.org/evasion_bchb.jpg"}, "File:Б\u200bч\u200bб сімволіка.jpg"),
        ({"url": "https://upload.wikimedia.org/march.jpg"}, "File:Марш новой беларуси у стелы.jpg"),
        ({"url": "https://upload.wikimedia.org/women.jpg"}, "File:Женский марш в Минске.jpg"),
        ({"url": "https://upload.wikimedia.org/protest2020.jpg"}, "File:Белорусские протесты 2020 года.jpg"),
    ]
    for info, title in samples:
        assert is_valid_photo(info, title=title) is False, f"Failed to reject BCHB/protest: {title}"

def test_validation_rejects_z_v_svo_and_military_conflict():
    """Verify rejection of Z, V, SVO, contemporary military conflict symbols, slogans, and monuments."""
    samples = [
        ({"url": "https://upload.wikimedia.org/tank.jpg"}, "File:Russian military vehicle with Z symbol.jpg"),
        ({"url": "https://upload.wikimedia.org/v_sym.jpg"}, "File:Armor with V symbol in conflict zone.jpg"),
        ({"url": "https://upload.wikimedia.org/v_text.jpg"}, "File:V-символ на военной технике.jpg"),
        ({"url": "https://upload.wikimedia.org/v_army.jpg"}, "File:V-армия на учениях.jpg"),
        ({"url": "https://upload.wikimedia.org/v_sign.jpg"}, "File:Знак V на броне.jpg"),
        ({"url": "https://upload.wikimedia.org/war_rus.jpg"}, "File:Русско-украинская война на Донбассе.jpg"),
        ({"url": "https://upload.wikimedia.org/war_against.jpg"}, "File:Война России против Украины 2022.jpg"),
        (
            {
                "url": "https://upload.wikimedia.org/war_cat.jpg",
                "extmetadata": {"Categories": {"value": "War in Ukraine|Military vehicles"}},
            },
            "File:combat_vehicle.jpg",
        ),
        (
            {
                "url": "https://upload.wikimedia.org/svo.jpg",
                "extmetadata": {"ImageDescription": {"value": "Памятник участникам СВО и спецоперации"}},
            },
            "File:monument_svo.jpg",
        ),
        (
            {
                "url": "https://upload.wikimedia.org/azov.jpg",
                "extmetadata": {"Categories": {"value": "Azov battalion fighters|War in Ukraine"}},
            },
            "File:azov_emblem.jpg",
        ),
        (
            {
                "url": "https://upload.wikimedia.org/slogan.jpg",
                "extmetadata": {"ImageDescription": {"value": "Лозунг Слава Украине! Героям слава!"}},
            },
            "File:graffiti_conflict.jpg",
        ),
        ({"url": "https://upload.wikimedia.org/wagner.jpg"}, "File:PMC Wagner group soldiers.jpg"),
        ({"url": "https://upload.wikimedia.org/dpr.jpg"}, "File:DPR soldiers in Donetsk.jpg"),
        (
            {
                "url": "https://upload.wikimedia.org/tank_destroyed.jpg",
                "extmetadata": {"ImageDescription": {"value": "Подбитый танк в ходе боевых действий"}},
            },
            "File:destroyed_tank.jpg",
        ),
        ({"url": "https://upload.wikimedia.org/zov.jpg"}, "File:ZOV пропаганда.jpg"),
        ({"url": "https://upload.wikimedia.org/evasion_z.jpg"}, "File:Z\u200b-symbol armored truck.jpg"),
        ({"url": "https://upload.wikimedia.org/goida.jpg"}, "File:Гойда концерт митинг.jpg"),
        ({"url": "https://upload.wikimedia.org/guard_ribbon.jpg"}, "File:Гвардейская лента на броне.jpg"),
        ({"url": "https://upload.wikimedia.org/crimea.jpg"}, "File:Аннексия Крыма военные.jpg"),
        ({"url": "https://upload.wikimedia.org/bridge.jpg"}, "File:Крымский мост взрыв повреждения.jpg"),
    ]
    for info, title in samples:
        assert is_valid_photo(info, title=title) is False, f"Failed to reject military conflict visual: {title}"

def test_validation_rejects_nazi_and_extremist_symbolism():
    """Verify rejection of Nazi, fascist, SS, and extremist visuals."""
    samples = [
        ({"url": "https://upload.wikimedia.org/swastika.jpg"}, "File:Nazi swastika banner.jpg"),
        (
            {
                "url": "https://upload.wikimedia.org/hitler.jpg",
                "extmetadata": {"ImageDescription": {"value": "Adolf Hitler in Berlin 1938"}},
            },
            "File:historical_photo.jpg",
        ),
        (
            {
                "url": "https://upload.wikimedia.org/ss.jpg",
                "extmetadata": {"Categories": {"value": "Waffen-SS uniforms|Third Reich"}},
            },
            "File:ss_soldiers.jpg",
        ),
        ({"url": "https://upload.wikimedia.org/fascist.jpg"}, "File:Fascist movement symbol.jpg"),
    ]
    for info, title in samples:
        assert is_valid_photo(info, title=title) is False, f"Failed to reject Nazi/extremist symbol: {title}"

def test_validation_rejects_violence_executions_burials_and_nsfw():
    """Verify rejection of executions, burials, corpses, and NSFW/nudity."""
    samples = [
        ({"url": "https://upload.wikimedia.org/corpse.jpg"}, "File:Exhumation of mass grave human remains.jpg"),
        (
            {
                "url": "https://upload.wikimedia.org/execution.jpg",
                "extmetadata": {"ImageDescription": {"value": "Публичная казнь и расстрел"}},
            },
            "File:execution_scene.jpg",
        ),
        (
            {
                "url": "https://upload.wikimedia.org/nude.jpg",
                "extmetadata": {"Categories": {"value": "Nudity|18+|NSFW model"}},
            },
            "File:erotic_photo.jpg",
        ),
    ]
    for info, title in samples:
        assert is_valid_photo(info, title=title) is False, f"Failed to reject violence/NSFW: {title}"

@pytest.mark.asyncio
async def test_report_and_block_photo_endpoints():
    """Verify POST /api/geo/pois/{id}/report-photo and block-photo workflow."""
    from src.routers.wikimedia_photos import report_photo, block_photo, wikimedia_photo, ReportPhotoRequest, BlockPhotoRequest
    from src.database.db import AsyncSessionLocal
    from src.database.models import Place
    from sqlalchemy import select

    test_pid = "test:moderation:001"
    async with AsyncSessionLocal() as session:
        existing = (await session.execute(select(Place).where(Place.place_id == test_pid))).scalar_one_or_none()
        if not existing:
            test_place = Place(
                place_id=test_pid,
                name="Тестовый объект модерации",
                city="Минск",
                region="Минская область",
                address="ул. Тестовая 1",
                category="monument",
                lat=53.9000,
                lon=27.5600,
            )
            session.add(test_place)
            await session.commit()

    # 1. Test photo report
    report_res = await report_photo(
        place_id=test_pid,
        body=ReportPhotoRequest(reason="political_content", details="Содержит запрещенную символику"),
    )
    assert report_res["status"] == "success"
    assert report_res["place_id"] == test_pid

    # 2. Test photo block
    block_res = await block_photo(
        place_id=test_pid,
        body=BlockPhotoRequest(reason="blocked_by_moderator"),
    )
    assert block_res["status"] == "success"
    assert block_res["photo"] is None

    # 3. Subsequent call to wikimedia_photo returns blocked: True, photo: None
    photo_res = await wikimedia_photo(test_pid)
    assert photo_res["photo"] is None
    assert photo_res.get("blocked") is True

@pytest.mark.asyncio
async def test_blocked_photo_serialization_in_api():
    """Verify that api_integrated photo helpers return None for blocked photos."""
    from src.database.models import PlacePhoto, Place
    from src.routers.api_integrated import _photo_images, photo_to_dict, place_to_dict, ensure_place_photo
    from src.database.db import AsyncSessionLocal

    blocked_photo = PlacePhoto(
        place_id="test:blocked:001",
        source="blocked",
        original_url="blocked",
        local_url_thumb=None,
        local_url_medium=None,
    )
    test_place = Place(
        place_id="test:blocked:001",
        name="Блокированное место",
        city="Минск",
        region="Минская область",
        lat=53.9,
        lon=27.56,
        category="misc",
    )

    # 1. _photo_images must return None, not {"thumb": "blocked", ...}
    images = _photo_images(blocked_photo)
    assert images is None

    # 2. photo_to_dict must return None
    assert photo_to_dict(blocked_photo) is None

    # 3. place_to_dict must have None image_url and images
    p_dict = place_to_dict(test_place, blocked_photo)
    assert p_dict["image_url"] is None
    assert p_dict["images"] is None

@pytest.mark.asyncio
async def test_api_pois_alias_endpoints():
    """Verify that /api/pois/{id}/report-photo and /api/pois/{id}/block-photo alias routes work."""
    from src.routers.wikimedia_photos import report_photo_pois_alias, block_photo_pois_alias, ReportPhotoRequest, BlockPhotoRequest
    from src.database.db import AsyncSessionLocal
    from src.database.models import Place
    from sqlalchemy import select

    test_pid = "test:alias:002"
    async with AsyncSessionLocal() as session:
        existing = (await session.execute(select(Place).where(Place.place_id == test_pid))).scalar_one_or_none()
        if not existing:
            session.add(Place(
                place_id=test_pid,
                name="Объект алиас",
                city="Гродно",
                region="Гродненская область",
                category="monument",
                lat=53.68,
                lon=23.83,
            ))
            await session.commit()

    rep = await report_photo_pois_alias(test_pid, ReportPhotoRequest(reason="bad_content"))
    assert rep["status"] == "success"

    blk = await block_photo_pois_alias(test_pid, BlockPhotoRequest(reason="admin_delete"))
    assert blk["status"] == "success"
    assert blk["photo"] is None

def test_legitimate_places_not_false_positives():
    """Verify that authentic Belarusian cultural assets and monuments are never false-positively rejected."""
    places = [
        "Брестская крепость-герой",
        "Мирский замок",
        "Национальная библиотека Беларуси",
        "Минск, Троицкое предместье",
        "Костел Святого Симеона и Святой Елены",
        "Церковь Рождества Богородицы",
        "Памятник Франциску Скорине",
        "Памятник Якубу Коласу",
        "Музей истории Великой Отечественной войны",
        "Мемориальный комплекс Хатынь",
        "Курган Славы",
        "Площадь Победы в Минске",
        "Парк Горького в Минске",
        "Белорусский государственный музей народной архитектуры и быта",
        "Братская могила советских воинов",
        "Памятник воинам-освободителям",
        "Monument to Janka Kupala",
        "Grodno Old Castle",
    ]
    for p in places:
        info = {
            "url": "https://upload.wikimedia.org/valid.jpg",
            "extmetadata": {"ImageDescription": {"value": p}},
        }
        assert is_valid_photo(info, title=f"File:{p}.jpg") is True, f"Legitimate place rejected as false-positive: {p}"

