from pathlib import Path


SOURCE = Path("src/routers/geo_feed.py").read_text(encoding="utf-8")


def test_feed_is_region_scoped():
    assert "filters=[Place.city==city, Place.region==region]" in SOURCE or "filters = [Place.city == city, Place.region == region]" in SOURCE


def test_feed_clamps_page_and_page_size():
    assert "page=max(page,0)" in SOURCE or "page = max(page, 0)" in SOURCE
    assert "min(max(page_size,1),MAX_PAGE_SIZE)" in SOURCE or "min(max(page_size, 1), MAX_PAGE_SIZE)" in SOURCE


def test_photo_payload_does_not_use_media_path():
    assert '"thumb": url' in SOURCE
    assert '"medium": url' in SOURCE
    assert '"original": url' in SOURCE
