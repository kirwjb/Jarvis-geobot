"""Pure filtering and scoring helpers for Wikimedia image search."""

import re

BELARUS_BBOX = {"min_lat": 51.25, "max_lat": 56.17, "min_lon": 23.17, "max_lon": 32.77}
BAD_EXTENSIONS = (".svg", ".pdf", ".djvu", ".tiff", ".tif", ".webm", ".ogv", ".mp4", ".mp3")
BAD_DESCRIPTION_WORDS = (
    "map of", "locator map", "location map", "map showing",
    "карта ", "карта:", "схема ", "схема:", "план ", "план:",
    "герб ", "герб:", "coat of arms", "flag of", "флаг ", "флаг:",
    "locator_map", "coat_of_arms", "flag_of"
)

CITY_SYNONYMS = {
    "минск": ("минск", "мінск", "minsk"),
    "брест": ("брест", "брэст", "brest", "беларусь", "беларус", "brest belarus", "brest region", "брестская область", "беларусь брест"),
    "брэст": ("брест", "брэст", "brest", "беларусь", "беларус", "brest belarus", "brest region", "брестская область", "беларусь брест"),
    "гродно": ("гродно", "гродна", "grodno", "hrodna"),
    "гродна": ("гродно", "гродна", "grodno", "hrodna"),
    "гомель": ("гомель", "homiel", "gomel"),
    "витебск": ("витебск", "віцебск", "vitebsk"),
    "віцебск": ("витебск", "віцебск", "vitebsk"),
    "могилев": ("могилев", "магілёў", "mogilev", "mogilyov"),
    "магілёў": ("могилев", "магілёў", "mogilev", "mogilyov"),
    "полоцк": ("полоцк", "полацк", "polotsk"),
    "полацк": ("полоцк", "полацк", "polotsk"),
    "пинск": ("пинск", "пінск", "pinsk"),
    "пінск": ("пинск", "пінск", "pinsk"),
    "борисов": ("борисов", "барысаў", "borisov", "barysaw"),
    "барысаў": ("борисов", "барысаў", "borisov", "barysaw"),
    "несвиж": ("несвиж", "нясвіж", "nesvizh"),
    "нясвіж": ("несвиж", "нясвіж", "nesvizh"),
    "слуцк": ("слуцк", "слуцак", "slutsk"),
    "слуцак": ("слуцк", "слуцак", "slutsk"),
}

CITY_LANG_MAP = {
    "могилев": {"ru": "Могилев", "be": "Магілёў", "en": "Mogilev"},
    "магілёў": {"ru": "Могилев", "be": "Магілёў", "en": "Mogilev"},
    "минск": {"ru": "Минск", "be": "Мінск", "en": "Minsk"},
    "мінск": {"ru": "Минск", "be": "Мінск", "en": "Minsk"},
    "брест": {"ru": "Брест", "be": "Брэст", "en": "Brest"},
    "брэст": {"ru": "Брест", "be": "Брэст", "en": "Brest"},
    "гродно": {"ru": "Гродно", "be": "Гродна", "en": "Grodno"},
    "гродна": {"ru": "Гродно", "be": "Гродна", "en": "Grodno"},
    "гомель": {"ru": "Гомель", "be": "Гомель", "en": "Gomel"},
    "витебск": {"ru": "Витебск", "be": "Віцебск", "en": "Vitebsk"},
    "віцебск": {"ru": "Витебск", "be": "Віцебск", "en": "Vitebsk"},
    "полоцк": {"ru": "Полоцк", "be": "Полацк", "en": "Polotsk"},
    "полацк": {"ru": "Полоцк", "be": "Полацк", "en": "Polotsk"},
    "пинск": {"ru": "Пинск", "be": "Пінск", "en": "Pinsk"},
    "пінск": {"ru": "Пинск", "be": "Пінск", "en": "Pinsk"},
    "несвиж": {"ru": "Несвиж", "be": "Нясвіж", "en": "Nesvizh"},
    "нясвіж": {"ru": "Несвиж", "be": "Нясвіж", "en": "Nesvizh"},
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

TRANSLIT_TABLE = str.maketrans({
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d",
    "е": "e", "ё": "e", "ж": "zh", "з": "z", "и": "i",
    "й": "j", "к": "k", "л": "l", "м": "m", "н": "n",
    "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
    "у": "u", "ф": "f", "х": "h", "ц": "c", "ч": "ch",
    "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "",
    "э": "e", "ю": "yu", "я": "ya", "ў": "u", "і": "i",
    "ґ": "g"
})

STOP_WORDS = {
    "год", "года", "годдзе", "годов", "лет",
    "the", "and", "for", "in", "of",
    "на", "в", "из", "и", "імя", "имени"
}

NOISE_WORDS = {
    "імя", "имени", "imya", "named after",
    "абласны", "абласная", "абласное", "областной", "областная", "областное", "regional",
    "гарадскі", "гарадская", "гарадское", "городской", "городская", "городское", "city",
    "раённы", "раённая", "раённае", "районный", "районная", "районное", "district",
    "дзяржаўны", "дзяржаўная", "дзяржаўнае", "государственный", "государственная", "государственное", "state",
    "рэспубліканскі", "рэспубліканская", "рэспубліканскае", "республиканский", "республиканская", "республиканское", "republican",
    "нацыянальны", "нацыянальная", "нацыянальнае", "национальный", "национальная", "национальное", "national",
    "філіял", "филиал", "branch",
    "ў горадзе", "у горадзе", "в городе",
    "прасвятой", "пресвятой", "святога", "святого", "святой",
    "belarus", "беларусь", "беларусі", "белоруссия", "belarusian", "белорусский", "беларускі"
}

CITY_ADJ_RE = re.compile(
    r'\b(магілёўск\w*|могилевск\w*|мінск\w*|минск\w*|брэсцк\w*|брестск\w*|гродзенск\w*|гродненск\w*|гомельск\w*|витебск\w*|віцебск\w*|полацк\w*|полоцк\w*|пінск\w*|пинск\w*|барысаўск\w*|борисовск\w*|нясвіжск\w*|несвижск\w*|мірск\w*|мирск\w*)\b',
    re.IGNORECASE
)
SUBTYPE_ADJ_RE = re.compile(
    r'\b(мастацк\w*|художественн\w*|гістарычн\w*|историческ\w*|краязнаўч\w*|краеведческ\w*|літаратурн\w*|литературн\w*|ваенн\w*|военн\w*|архітэктурн\w*|архитектурн\w*)\b',
    re.IGNORECASE
)

INITIALS_RE = re.compile(r'\b[А-ЯЁІЎA-Z]\.\s*(?:[А-ЯЁІЎA-Z]\.\s*)?', re.UNICODE)
PUNCT_RE = re.compile(r'[\"«»\'’\(\)\[\],;:!\?]', re.UNICODE)

EXHIBIT_KEYWORDS = (
    "картина", "жывапіс", "живопись", "экспонат", "экспанат",
    "выстава", "выставка", "икона", "ікона", "партрэт", "портрет",
    "пастэль", "пастель", "палатно", "полотно", "алей", "масло",
    "банкнота", "монета", "рублей", "рублёў", "оклад",
    "музейны прадмет", "захаваная спадчына", "painting", "exhibit",
    "artwork", "coin", "banknote", "icon"
)

TYPE_NOUNS = {
    "музей", "замак", "замок", "царква", "церковь", "касцёл", "костёл",
    "храм", "собор", "палац", "дворец", "парк", "галерэя", "галерея",
    "тэатр", "театр", "помнік", "памятник", "мемарыял", "мемориал",
    "сядзіба", "усадьба", "крэпасць", "крепость", "вежа", "башня",
    "бібліятэка", "библиотека"
}


def normalize_text(value: str) -> str:
    """Normalize Wikimedia titles, descriptions and search terms."""
    if not value:
        return ""
    value = str(value).lower().replace("file:", "").replace("&quot;", " ").replace("&#39;", "'")
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
    """Return proximity bonus for Wikimedia ranking."""
    if photo_lat is None or photo_lon is None:
        return 0
    try:
        distance = ((float(object_lat) - float(photo_lat)) ** 2 + (float(object_lon) - float(photo_lon)) ** 2) ** 0.5
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


def is_valid_photo(info: dict, title: str = "") -> bool:
    """Check if the asset is a valid visual.

    Softened validation:
    - Rejects truly invalid non-visuals: missing URL, vector SVG, documents PDF/DJVU, video/audio.
    - Rejects pure maps, schemes, coats of arms, flags.
    - Only rejects dimensions if they are known AND strictly tiny (< 150px).
    - NEVER rejects non-Latin filenames (Cyrillic, Belarusian, etc.).
    - NEVER rejects paintings or museum exhibits here (they are handled as fallback candidates).
    """
    url = (info.get("url") or "").strip().lower()
    if not url or any(url.endswith(ext) for ext in BAD_EXTENSIONS):
        return False

    norm_title = (title or "").lower().replace("_", " ")
    for bad_kw in ("coat of arms", "flag of", "locator map", "map of", "герб ", "флаг ", "схема ", "карта "):
        if bad_kw in norm_title:
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
        width = int(info.get("width") or info.get("thumbwidth") or 0)
        height = int(info.get("height") or info.get("thumbheight") or 0)
    except (TypeError, ValueError):
        width, height = 0, 0

    if width > 0 and height > 0 and (width < 150 or height < 150):
        return False

    return True


def is_secondary_visual(info: dict, title: str = "") -> bool:
    """Detect whether the image is an exhibit, painting, artwork, or interior artifact.

    Used by the pipeline to distinguish between primary exterior/building photos
    and secondary visual fallbacks so exhibits are retained as fallbacks rather
    than discarding visual items entirely.
    """
    lower_title = (title or "").lower()
    if any(kw in lower_title for kw in EXHIBIT_KEYWORDS):
        return True

    metadata = info.get("extmetadata", {})
    description = str(
        metadata.get("ImageDescription", {}).get("value")
        or metadata.get("ObjectName", {}).get("value")
        or ""
    ).lower()
    if any(kw in description for kw in EXHIBIT_KEYWORDS):
        return True

    categories = str(metadata.get("Categories", {}).get("value") or "").lower()
    if any(kw in categories for kw in ("paintings", "exhibits", "collections", "icons", "banknotes", "coins")):
        return True

    return False


def _stem_matches(w1: str, w2: str) -> bool:
    """Check if two words share a common stem or inflected prefix."""
    s1, s2 = normalize_text(w1), normalize_text(w2)
    if not s1 or not s2:
        return False
    if s1 in s2 or s2 in s1:
        return True
    if len(s1) >= 5 and len(s2) >= 5 and (s1[:5] in s2 or s2[:5] in s1):
        return True
    return False


def match_score(
    title: str,
    name: str,
    city: str,
    extra_words: str = "",
    metadata: dict | None = None,
) -> int:
    """Score how strongly a Wikimedia file matches an OSM place.

    Supports title forms, inflected stem matching, and metadata/description matching.
    """
    title_forms = text_forms(title)
    name_forms = text_forms(name)
    if not title_forms or not name_forms:
        return 0

    score = 0

    # 1. Direct form containment
    for name_form in name_forms:
        for title_form in title_forms:
            if name_form and name_form in title_form:
                score = max(score, 100)

    # 2. Word matching with stem support
    clean_words = [
        word for word in normalize_text(name).split()
        if len(word) >= 3 and word not in STOP_WORDS and word not in NOISE_WORDS
    ]
    if clean_words:
        matched = 0
        for word in clean_words:
            matched_word = False
            for word_form in text_forms(word):
                for title_form in title_forms:
                    if word_form in title_form or any(_stem_matches(word_form, t_word) for t_word in title_form.split()):
                        matched_word = True
                        break
                if matched_word:
                    break
            if matched_word:
                matched += 1

        ratio = matched / len(clean_words)
        if ratio >= 0.75:
            score += 80
        elif ratio >= 0.50:
            score += 55
        elif ratio >= 0.30:
            score += 30
        elif matched:
            score += 15

    # 3. City bonus
    if any(
        form in title_form
        for variant in city_variants(city)
        for form in text_forms(variant)
        for title_form in title_forms
    ):
        score += 30

    # 4. Extra type words bonus
    if extra_words:
        type_words = [word for word in normalize_text(extra_words).split() if len(word) >= 4]
        if any(form in title_form for word in type_words for form in text_forms(word) for title_form in title_forms):
            score += 15

    # 5. Metadata / description evaluation
    if metadata and score < 50:
        desc = str(
            metadata.get("ImageDescription", {}).get("value")
            or metadata.get("ObjectName", {}).get("value")
            or metadata.get("Categories", {}).get("value")
            or ""
        )
        desc_forms = text_forms(desc)
        for name_form in name_forms:
            if any(name_form and name_form in df for df in desc_forms):
                score = max(score, 55)
                break
        if score < 50 and clean_words:
            desc_matched = sum(1 for w in clean_words if any(w in df for df in desc_forms))
            if desc_matched / len(clean_words) >= 0.5:
                score = max(score, 45)

    # Brest disambiguation check
    if normalize_text(city) in ("брест", "брэст"):
        title_text = " ".join(title_forms)
        belarus_markers = ("belarus", "беларус", "brest belarus", "brest region", "брестская область", "брэсцкая")
        if not any(marker in title_text for marker in belarus_markers):
            score = min(score, 95)

    return score


# ---------------------------------------------------------------------------
# Cascading Query Normalizer
# ---------------------------------------------------------------------------

def be_to_ru(text: str) -> str:
    """Convert common Belarusian orthography patterns to Russian for search fallback."""
    res = text.replace("і", "и").replace("І", "И")
    res = res.replace("ў", "в").replace("Ў", "В")
    res = res.replace("’", "").replace("'", "")
    res = re.sub(r'(\w+)ікава\b', r'\1икова', res)
    res = re.sub(r'(\w+)енікава\b', r'\1еникова', res)
    res = re.sub(r'(\w+)ава\b', r'\1ова', res)
    res = re.sub(r'\bзамак\b', 'замок', res)
    res = re.sub(r'\bцарква\b', 'церковь', res)
    res = re.sub(r'\bпалац\b', 'дворец', res)
    res = re.sub(r'\bгалерэя\b', 'галерея', res)
    res = re.sub(r'\bмастацкі\b', 'художественный', res)
    res = re.sub(r'\bкраязнаўчы\b', 'краеведческий', res)
    res = re.sub(r'\bгістарычны\b', 'исторический', res)
    res = re.sub(r'\bпомнік\b', 'памятник', res)
    res = re.sub(r'\bкрэпасць\b', 'крепость', res)
    return res


def clean_place_name(name: str) -> str:
    """Strip quotes, punctuation, initials and institutional noise words from a place name."""
    if not name:
        return ""
    # Strip quotes, punctuation, brackets
    cleaned = PUNCT_RE.sub(" ", name)
    # Strip initials (e.g. П. В., А. С., Я.)
    cleaned = INITIALS_RE.sub(" ", cleaned)
    tokens = [t.strip() for t in cleaned.split() if t.strip()]
    # Remove noise / stop words
    meaningful = [t for t in tokens if t.lower() not in NOISE_WORDS and t.lower() not in STOP_WORDS]
    return " ".join(meaningful).strip()


def extract_core_keywords(name: str) -> tuple[str | None, str | None]:
    """Extract object type noun and main proper noun/surname from a place name."""
    cleaned = clean_place_name(name)
    tokens = cleaned.split()
    if not tokens:
        return None, None

    type_word = None
    proper_tokens = []
    subtype_tokens = []

    for token in tokens:
        lower = token.lower()
        if lower in TYPE_NOUNS and not type_word:
            type_word = token
        elif CITY_ADJ_RE.match(token):
            continue
        elif SUBTYPE_ADJ_RE.match(token):
            subtype_tokens.append(token)
        else:
            proper_tokens.append(token)

    if not proper_tokens:
        if subtype_tokens:
            proper_tokens = subtype_tokens
        else:
            proper_tokens = [t for t in tokens if t.lower() not in TYPE_NOUNS]

    proper_name = " ".join(proper_tokens).strip() or None
    return type_word, proper_name


def generate_cascading_queries(
    name: str,
    city: str,
    category: str = "",
    osm_tags: dict | None = None,
) -> list[str]:
    """Generate clean, cascading search queries for Wikimedia Commons.

    Strips punctuation, quotes, initials, and noise words.
    Produces clean language-consistent variants (e.g. 'Музей Масленікава Магілёў'
    and 'Музей Масленикова') without mixed-language noise.
    """
    clean_name = clean_place_name(name)
    if not clean_name:
        return [name.strip()] if name else []

    norm_city = normalize_text(city)
    city_langs = CITY_LANG_MAP.get(norm_city, {})
    ru_city = city_langs.get("ru", city.strip())
    be_city = city_langs.get("be", city.strip())

    type_word, proper_name = extract_core_keywords(name)

    ru_name = be_to_ru(clean_name)
    ru_proper = be_to_ru(proper_name) if proper_name else None
    ru_type = be_to_ru(type_word) if type_word else None

    # Include explicit OSM multilingual names if available
    osm_names = []
    if osm_tags:
        for key in ("name:ru", "name:be", "name:en"):
            val = osm_tags.get(key)
            if val and val != name:
                cleaned_osm = clean_place_name(val)
                if cleaned_osm:
                    osm_names.append(cleaned_osm)

    queries: list[str] = []

    def _add(q: str):
        q = re.sub(r"\s+", " ", q).strip()
        if q and q not in queries:
            queries.append(q)

    # 1. Type + Proper Name + City (Belarusian / native)
    if type_word and proper_name:
        _add(f"{type_word} {proper_name} {be_city}")
        if ru_type and ru_proper:
            _add(f"{ru_type} {ru_proper} {ru_city}")
        _add(f"{type_word} {proper_name}")
        if ru_type and ru_proper:
            _add(f"{ru_type} {ru_proper}")

    # 2. Clean Name + City
    _add(f"{clean_name} {be_city}")
    _add(f"{ru_name} {ru_city}")

    # 3. OSM multilingual names
    for oname in osm_names:
        _add(f"{oname} {ru_city}")
        _add(oname)

    # 4. Clean Name alone
    _add(clean_name)
    _add(ru_name)

    # 5. Proper Name + City
    if proper_name:
        _add(f"{proper_name} {be_city}")
        if ru_proper:
            _add(f"{ru_proper} {ru_city}")
        _add(proper_name)
        if ru_proper:
            _add(ru_proper)

    # 6. Type words from category
    type_hint = TYPE_QUERY_WORDS.get(category.lower(), "")
    if type_hint and proper_name:
        first_type = type_hint.split()[0]
        _add(f"{proper_name} {first_type} {be_city}")

    return queries


def generate_category_search_queries(
    name: str,
    city: str,
    category: str = "",
    osm_tags: dict | None = None,
) -> list[str]:
    """Generate search terms for locating Wikimedia Commons Category pages (namespace 14)."""
    type_word, proper_name = extract_core_keywords(name)
    clean_name = clean_place_name(name)
    ru_name = be_to_ru(clean_name)
    ru_proper = be_to_ru(proper_name) if proper_name else None
    ru_type = be_to_ru(type_word) if type_word else None

    norm_city = normalize_text(city)
    city_langs = CITY_LANG_MAP.get(norm_city, {})
    ru_city = city_langs.get("ru", city.strip())
    be_city = city_langs.get("be", city.strip())

    queries: list[str] = []

    def _add(q: str):
        q = re.sub(r"\s+", " ", q).strip()
        if q and q not in queries:
            queries.append(q)

    if type_word and proper_name:
        _add(f"{type_word} {proper_name}")
        if ru_type and ru_proper:
            _add(f"{ru_type} {ru_proper}")
        _add(f"{type_word} {proper_name} {be_city}")
        if ru_type and ru_proper:
            _add(f"{ru_type} {ru_proper} {ru_city}")

    _add(clean_name)
    _add(ru_name)
    if proper_name:
        _add(proper_name)
        if ru_proper:
            _add(ru_proper)

    if osm_tags:
        for key in ("name:ru", "name:be", "name:en"):
            val = osm_tags.get(key)
            if val:
                c = clean_place_name(val)
                if c:
                    _add(c)

    return queries
