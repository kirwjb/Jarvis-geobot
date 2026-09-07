from src.routers import geo_feed


def test_page_size_bounds():
    # Keep the public contract bounded even when callers send extreme values.
    assert geo_feed.PAGE_SIZE == 8
    assert geo_feed.MAX_PAGE_SIZE == 30


def test_marker_key_is_region_scoped():
    assert geo_feed._marker_key("Минск", "Минская область") != geo_feed._marker_key("Минск", "Гродненская область")
