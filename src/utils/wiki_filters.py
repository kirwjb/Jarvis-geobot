"""Pure filtering and scoring helpers for Wikimedia image search."""

import re


BELARUS_BBOX = {
    "min_lat": 51.25,
    "max_lat": 56.17,
    "min_lon": 23.17,
    "max_lon": 32.77,
}

BAD_EXTENSIONS = (".svg", ".pdf", ".djvu", ".tiff", ".tif")

BAD_DESCRIPTION_WORDS = (
    "map of",
    "locator map",
    "location map",
    "map showing",
    "карта ",
    "карта:",
    "схема ",
    "схема:",
    "план ",
    "план:",
    "герб ",
    "герб:",
    "coat of arms",
    "flag of",
    "флаг ",
    "флаг:",
)

# Brest is ambiguous: there is a large city in Belarus and a city in France.
# Keep the bare city forms for filename scoring, but do not treat a Commons
# category named simply "Brest" as proof that a file belongs to Belarus.
CITY_SYNONYMS = {
    "минск": ("минск", "мінск", "minsk"),
    "брест": ("беларусь", "беларус", "brest belarus", "brest region", "брестская область", "беларусь брест"),
    "гродно": ("гродно", "гродна", "grodno", "hrodna"),
    "гомель": ("гомель", "homiel", "gomel"),
    "витебск": ("витебск", "віцебск", "vitebsk"),
    "могилев": ("могилев", "магілёў", "mogilev", "mogilyov"),
    "полоцк": ("полоцк", "полацк", "polotsk"),
    "пинск": ("пинск", "пінск", "pinsk"),
    "борисов": ("борисов", "барысаў", "borisov", "barysaw"),
    "несвиж": ("несвиж", "нясвіж", "nesvizh"),
    "слуцк": ("слуцк", "слуцак", "slutsk"),
}

TYPE_QUERY_WORDS = {
    "memorial": "memorial памятник помнік monument мемориал мемарыял",
    "monument": "monument памятник помнік мемориал мемарыял",
    "church": "church church building церковь царква касцёл костёл храм собор",
    "castle": "castle замок замак palace дворец палац",
    "museum": "museum музей",
    "manor": "manor усадьба сядзіба palace дворец палац",
    "ruins": "ruins руины руіны",
    "park": "park парк",
    "viewpoint": "viewpoint панорама смотровая площадка",
    "gallery": "gallery галерея",
    "theme_park": "theme park парк аттракционов",
}

TRANSLIT_TABLE = str.maketrans(
    {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d",
        "е": "e", "ё": "e", "ж": "zh", "з": "z", "и": "i",
        "й": "j", "к": "k", "л": "l", "м": "m", "н": "n",
        "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
        "у": "u", "ф": "f", "х": "h", "ц": "c", "ч": "ch",
        "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "",
        "э": "e", "ю": "yu", "я": "ya", "ў": "u", "і": "i",
        "ґ": "g",
    }
)

STOP_WORDS = {
    "год", "года", "годдзе", "годов", "лет", "the", "and", "for",
    "in", "of", "на", "в", "из", "и", "імя", "имени",
}


def normalize_text(value: str) -> str:
    """Normalize Wikimedia titles, descriptions and search terms."""
    if not value:
        return ""

    value = str(value).lower()
    value = value.replace("file:", "")
    value = value.replace("&quot;", " ")
    value = value.replace("&#39;", "'")
    value = re.sub(r"[^a-zа-яёіўґ0-9\s]", " ", value, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", value).strip()


def translit(value: str) -> str:
    """Transliterate normalized Cyrillic text to Latin."""
    return normalize_text(value).translate(TRANSLIT_TABLE)


def text_forms(value: str) -> set[str]:
    """Return normalized and transliterated forms for matching."""
    normalized = normalize_text(value)
    if not normalized:
        return set()

    forms = {normalized}
    transliterated = translit(normalized)
    if transliterated:
        forms.add(transliterated)
    return forms


def city_variants(city: str) -> list[str]:
    """Return normalized, transliterated and known synonym forms."""
    normalized = normalize_text(city)
    if not normalized:
        return []

    # Always keep the canonical city name for filename scoring.
    variants = {normalized}
    transliterated = translit(normalized)
    if transliterated:
        variants.add(transliterated)

    for base, synonyms in CITY_SYNONYMS.items():
        normalized_synonyms = {normalize_text(item) for item in synonyms}
        if normalized == base or normalized in normalized_synonyms:
            variants.add(normalize_text(base))
            variants.update(normalized_synonyms)

    return [variant for variant in variants if variant]


def is_in_belarus(lat: float, lon: float) -> bool:
    """Fast Belarus bounding-box check."""
    return (
        BELARUS_BBOX["min_lat"] <= lat <= BELARUS_BBOX["max_lat"]
        and BELARUS_BBOX["min_lon"] <= lon <= BELARUS_BBOX["max_lon"]
    )


def distance_score(
    object_lat: float,
    object_lon: float,
    photo_lat: float | None,
    photo_lon: float | None,
) -> int:
    """Return a coarse proximity bonus for Wikimedia ranking."""
    if photo_lat is None or photo_lon is None:
        return 0

    try:
        distance = (
            (float(object_lat) - float(photo_lat)) ** 2
            + (float(object_lon) - float(photo_lon)) ** 2
        ) ** 0.5
    except (TypeError, ValueError):
        return 0

    if distance <= 0.001:
        return 120
    if distance <= 0.003:
        return 100
    if distance <= 0.01:
        return 70
    if distance <= 0.03:
        return 40
    if distance <= 0.08:
        return 20
    return 0


def is_valid_photo(info: dict) -> bool:
    """Reject non-images, maps/diagrams and undersized files."""
    url = (info.get("url") or "").lower()
    if not url or url.endswith(BAD_EXTENSIONS):
        return False

    metadata = info.get("extmetadata", {})
    description = str(
        metadata.get("ImageDescription", {}).get("value")
        or metadata.get("ObjectName", {}).get("value")
        or ""
    ).lower()

    if any(word in description for word in BAD_DESCRIPTION_WORDS):
        return False

    try:
        width = int(info.get("width", 0) or 0)
        height = int(info.get("height", 0) or 0)
    except (TypeError, ValueError):
        return False

    return width >= 600 and height >= 400


def match_score(
    title: str,
    name: str,
    city: str,
    extra_words: str = "",
) -> int:
    """Score how strongly a Wikimedia filename matches an OSM place."""
    title_forms = text_forms(title)
    name_forms = text_forms(name)
    if not title_forms or not name_forms:
        return 0

    score = 0

    for name_form in name_forms:
        for title_form in title_forms:
            if name_form and name_form in title_form:
                score = max(score, 100)

    name_words = [
        word for word in normalize_text(name).split()
        if len(word) >= 3 and word not in STOP_WORDS
    ]

    if name_words:
        matched = 0
        for word in name_words:
            if any(
                word_form in title_form
                for word_form in text_forms(word)
                for title_form in title_forms
            ):
                matched += 1

        ratio = matched / len(name_words)
        if ratio >= 0.75:
            score += 80
        elif ratio >= 0.50:
            score += 55
        elif ratio >= 0.30:
            score += 30
        elif matched:
            score += 15

    if any(
        form in title_form
        for variant in city_variants(city)
        for form in text_forms(variant)
        for title_form in title_forms
    ):
        score += 30

    if extra_words:
        type_words = [
            word for word in normalize_text(extra_words).split()
            if len(word) >= 4
        ]
        if any(
            form in title_form
            for word in type_words
            for form in text_forms(word)
            for title_form in title_forms
        ):
            score += 15

    return score
