from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_city_selection_uses_stable_city_value():
    main = (ROOT / "frontend/js/main.js").read_text(encoding="utf-8")
    travel = (ROOT / "frontend/js/features/travel.js").read_text(encoding="utf-8")
    assert "pickCity(el.dataset.city)" in main
    assert 'data-city="${esc(c.name)}"' in travel
    assert "pickCity(Number(el.dataset.index))" not in main


def test_feed_pagination_is_server_driven_and_persisted():
    places = (ROOT / "frontend/js/features/places.js").read_text(encoding="utf-8")
    assert "data-action=\"page-prev\"" in places
    assert "data-action=\"page-next\"" in places
    assert "state.feed={key,search,shuffle,page,pages,total,pois}" in places
    assert "page_size:String(PAGE)" in places


def test_frontend_does_not_use_legacy_pois_query_for_feed():
    places = (ROOT / "frontend/js/features/places.js").read_text(encoding="utf-8")
    assert "/geo/pois/feed?" in places
    assert "/pois/query" not in places
