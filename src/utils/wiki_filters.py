"""Pure filtering and scoring helpers for Wikimedia image search."""

import re
import unicodedata

BELARUS_BBOX = {"min_lat": 51.25, "max_lat": 56.17, "min_lon": 23.17, "max_lon": 32.77}
BAD_EXTENSIONS = (".svg", ".pdf", ".djvu", ".tiff", ".tif", ".webm", ".ogv", ".mp4", ".mp3")
BAD_DESCRIPTION_WORDS = (
    "map of", "locator map", "location map", "map showing",
    "карта ", "карта:", "схема ", "схема:", "план ", "план:",
    "герб ", "герб:", "coat of arms", "flag of", "флаг ", "флаг:",
    "locator_map", "coat_of_arms", "flag_of"
)

ZERO_WIDTH_AND_INVISIBLE_RE = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff\u00ad]")

def clean_filter_text(text: str) -> str:
    """Normalize unicode to NFKC and strip zero-width characters and invisible noise."""
    if not text:
        return ""
    norm = unicodedata.normalize("NFKC", str(text))
    return ZERO_WIDTH_AND_INVISIBLE_RE.sub("", norm).lower()

# 1. Flag & Protest (BCHB, White-Red-White, protest symbolism)
PROTEST_BCHB_PATTERNS = [
    r"\bб[-.]?ч[-.]?б\b",
    r"\bb[-.]?c[-.]?h[-.]?b\b",
    r"\bбел[ао]?[- ]красно[- ]бел\w*",
    r"\bбел[ао]?[- ]чырвона[- ]бел\w*",
    r"\bwhite[- ]red[- ]white\b",
    r"\bwrw\s+flag\w*\b",
    r"\bжыве\s+беларусь\b",
    r"\bживе\s+беларусь\b",
    r"\bzhive\s+belarus\b",
    r"\bzyve\s+belarus\b",
    r"\blong\s+live\s+belarus\b",
    r"\bзмагар\w*",
    r"\bпротест\w*\s+(?:в|на)\s+беларус\w*",
    r"\bпротест\w*\s+в\s+минск\w*",
    r"\bпратэст\w*\s+(?:ў|у)\s+беларус\w*",
    r"\bбелорусск\w*\s+протест\w*",
    r"\bбеларуск\w*\s+пратэст\w*",
    r"\bbelarusian\s+protest\w*",
    r"\b2020\s+belarusian\s+protest\w*",
    r"\bмарш\s+(?:единства|новой\s+беларуси|героев|свободы|народовластия|женский|пенсионеров|мудрости)\b",
    r"\bженск\w*\s+марш\w*",
    r"\bсвято[- ]владимирск\w*\s+лент\w*",
    r"\bкоординационн\w*\s+совет\s+беларус\w*",
]

# 2. Russia / Ukraine contemporary military conflict, Z/V, SVO, military vehicles, slogans, conflict monuments
MILITARY_CONFLICT_PATTERNS = [
    r"\bсво\b",
    r"\bв\s+зоне\s+сво\b",
    r"\bгерои?\s+сво\b",
    r"\bучастник\w*\s+сво\b",
    r"\bспецопераци\w*",
    r"\bspecial\s+military\s+operation\b",
    r"\bденацификаци\w*",
    r"\bдемилитаризаци\w*",
    r"(?:\b|^|\s)[zZvVвВ]\s*[-_/]?\s*(?:символ\w*|знак\w*|symbol\w*|propaganda|patriot\w*|патриот\w*|операци\w*|арми\w*|войск\w*|войн\w*|za|zа|forces|military|vehicle|tank|armor|weapon|action)\b",
    r"\b(?:символ|знак|буква|symbol)\s*[zZvVвВ]\b",
    r"\b[zZvVвВ]\s+symbol\b",
    r"\b[zZvVвВ][-_](?:army|forces|symbol|operation|propaganda|patriot|войска|знак|символ|армия)\b",
    r"\bcategory\s*:\s*[zZvV]\s*\(",
    r"\bza\s+наших\b|\bza\s+россию\b|\bza\s+мир\b|\bсилы\s+[zZvV]\b",
    r"\bzov\b|\bz[- ]o[- ]v\b",
    r"\bгойда\b",
    r"\bслава\s+украин\w*",
    r"\bгероям\s+слава\b",
    r"\bslava\s+ukraini\b",
    r"\bglory\s+to\s+ukraine\b",
    r"\bбандер\w*",
    r"\bbandera\b",
    r"\bоун[- ]упа\b",
    r"\boun[- ]upa\b",
    r"\bазов\b",
    r"\bazov\s+(?:regiment|battalion|brigade|movement)\b",
    r"\bполк\s+азов\b",
    r"\bбатальон\s+азов\b",
    r"\bкракен\b",
    r"\bkraken\s+(?:regiment|unit)\b",
    r"\brusso[- ]ukrainian\s+war\b",
    r"\bwar\s+in\s+ukraine\b",
    r"\bukraine\s+war\b",
    r"\brussian\s+invasion\s+of\s+ukraine\b",
    r"\b(?:российско|русско)[- ]украинск\w*\s+(?:войн\w*|конфликт\w*)",
    r"\bвойн\w*\s+(?:в|на|против|с)\s+украин\w*",
    r"\bвойн\w*\s+росси\w*\s+против\s+украин\w*",
    r"\bвоенн\w*\s+операци\w*\s+(?:в|на)\s+украин\w*",
    r"\bвторжени\w*\s+(?:в|на)\s+украин\w*",
    r"\bвторжени\w*\s+росси\w*",
    r"\bроссийск\w*\s+агресси\w*",
    r"\bагресси\w*\s+(?:росси\w*|рф)\s+против\s+украин\w*",
    r"\bбоевые\s+действия\s+в\s+украин\w*",
    r"\bвсу\b",
    r"\bвооруженн\w*\s+сил\w*\s+украин\w*",
    r"\bukrainian\s+armed\s+forces\b",
    r"\barmed\s+forces\s+of\s+ukraine\b",
    r"\bzsu\b",
    r"\bвс\s+рф\b",
    r"\bвооруженн\w*\s+сил\w*\s+рф\b",
    r"\bвооруженн\w*\s+сил\w*\s+российской\s+федерации\b",
    r"\bчвк\s+вагнер\w*",
    r"\bwagner\s+group\b",
    r"\bpmc\s+wagner\b",
    r"\bднр\b|\bлнр\b|\bdpr\b|\blpr\b",
    r"\bдонецк\w*\s+народн\w*\s+республик\w*",
    r"\bluhansk\s+people'?s\s+republic\b",
    r"\bdonetsk\s+people'?s\s+republic\b",
    r"\bлуганск\w*\s+народн\w*\s+республик\w*",
    r"\bноворосси\w*",
    r"\bnovorossiya\b",
    r"\bгеоргиевск\w*\s+лент\w*",
    r"\bгвардейск\w*\s+лент\w*",
    r"\bgeorgievskaya\s+ribbon\b",
    r"\bst\.?\s*george\s+ribbon\b",
    r"\bаннекси\w*\s+крым\w*",
    r"\bоккупаци\w*\s+крым\w*",
    r"\bannexation\s+of\s+crimea\b",
    r"\bкрымск\w*\s+мост\w*\s+(?:взрыв\w*|теракт\w*|атак\w*|поврежден\w*|удар\w*)",
    r"\bdestroyed\s+(?:russian|ukrainian)\s+tank\b",
    r"\bподбит\w*\s+танк\w*",
    r"\bвоенн\w*\s+техник\w*\s+сво\b",
    r"\bпамятник\w*\s+героям\s+сво\b",
    r"\bмемориал\w*\s+героям\s+сво\b",
    r"\bпамятник\w*\s+погибшим\s+в\s+сво\b",
    r"\bрусский\s+военный\s+корабль\b",
]

# 3. Nazi & Extremist Symbolism
NAZI_EXTREMIST_PATTERNS = [
    r"\bсвастик\w*",
    r"\bswastika\b",
    r"\bhakenkreuz\b",
    r"\bnazi\w*",
    r"\bнацист\w*",
    r"\bнацизм\b",
    r"\bфашизм\b",
    r"\bфашист\w*",
    r"\bfascism\b",
    r"\bfascist\b",
    r"\bthird\s+reich\b",
    r"\bтрет\w*\s+рейх\w*",
    r"\bdrittes\s+reich\b",
    r"\b3rd\s+reich\b",
    r"\b(?:waffen[- ])?ss\b",
    r"\bваффен[- ]сс\b",
    r"\btotenkopf\b",
    r"\bмертв\w*\s+голов\w*",
    r"\bмёртв\w*\s+голов\w*",
    r"\bгитлер\w*",
    r"\bhitler\w*",
    r"\bадольф\s+гитлер\w*",
    r"\badolf\s+hitler\b",
    r"\bku\s+klux\s+klan\b",
    r"\bку[- ]клукс[- ]клан\b",
    r"\bнеонаци\w*",
    r"\bneonazi\w*",
    r"\bwhite\s+supremacy\b",
    r"\bwhite\s+supremacist\w*",
]

# 4. Violence, Executions, Burials/Corpses, 18+/NSFW/Nudity
VIOLENCE_NSFW_PATTERNS = [
    r"\bexecution\b",
    r"\bказн\w*",
    r"\bрасстрел\w*",
    r"\bповешени\w*",
    r"\bmassacre\b",
    r"\bмассов\w*\s+убийств\w*",
    r"\bгеноцид\w*",
    r"\blynching\b",
    r"\bлинчевани\w*",
    r"\bcorpse\w*",
    r"\bтруп\w*",
    r"\bdead\s+bod\w*",
    r"\bhuman\s+remains\b",
    r"\bостанк\w*\s+людей\b",
    r"\bчереп\s+человека\b",
    r"\bэксгумаци\w*",
    r"\bexhumation\b",
    r"\bmorgue\b",
    r"\bморг\b",
    r"\btorture\w*",
    r"\bпытк\w*",
    r"\bзахоронени\w*",
    r"\bmass\s+grave\w*",
    r"\bnsfw\b",
    r"\b18\+\b",
    r"\bnudity\b",
    r"\bnude\b",
    r"\bnaked\b",
    r"\bобнаженн\w*",
    r"\bобнажённ\w*",
    r"\bнагот\w*",
    r"\bпорно\w*",
    r"\bporn\w*",
    r"\berotic\w*",
    r"\bэротик\w*",
    r"\bэротическ\w*",
    r"\bgenitals\b",
    r"\bпенис\b",
    r"\bвагин\w*",
    r"\bсиськ\w*",
    r"\bгрудь\s+обнаженн\w*",
]

ALL_BLOCKED_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in (
        PROTEST_BCHB_PATTERNS
        + MILITARY_CONFLICT_PATTERNS
        + NAZI_EXTREMIST_PATTERNS
        + VIOLENCE_NSFW_PATTERNS
    )
]

def is_sensitive_or_blocked_content(text: str) -> bool:
    """Check if the text contains unwanted, political, extremist, violent, or sensitive tokens."""
    if not text:
        return False
    cleaned = clean_filter_text(text)
    for pattern in ALL_BLOCKED_PATTERNS:
        if pattern.search(cleaned):
            return True
    collapsed = re.sub(r"[-_.\s]+", "", cleaned)
    if any(k in collapsed for k in ("бчб", "bchb", "zov", "ounupa")):
        return True
    return False

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

    Validation rules:
    - Rejects truly invalid non-visuals: missing URL, vector SVG, documents PDF/DJVU, video/audio.
    - Rejects pure maps, schemes, coats of arms, flags.
    - Rejects sensitive, political, extremist, violent, and NSFW content (BCHB, Z/SVO/conflict, Nazi, etc.).
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
        or info.get("description")
        or ""
    ).lower()
    object_name = str(metadata.get("ObjectName", {}).get("value") or "").lower()
    artist = str(metadata.get("Artist", {}).get("value") or "").lower()
    if any(word in description or word in object_name for word in BAD_DESCRIPTION_WORDS):
        return False

    categories = str(metadata.get("Categories", {}).get("value") or "").lower()
    info_title = str(info.get("title") or "").lower()

    # Strict check against political, extremist, violent, conflict and NSFW content
    text_corpus = f"{norm_title} {info_title} {description} {object_name} {artist} {categories}"
    if is_sensitive_or_blocked_content(text_corpus):
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
    if is_sensitive_or_blocked_content(title):
        return 0
    if metadata:
        meta_text = str(
            metadata.get("ImageDescription", {}).get("value")
            or metadata.get("ObjectName", {}).get("value")
            or metadata.get("Categories", {}).get("value")
            or ""
        )
        if is_sensitive_or_blocked_content(meta_text):
            return 0

    title_forms = text_forms(title)
    name_forms = text_forms(name)
    if not title_forms or not name_forms:
        return 0

    score = 0

    for name_form in name_forms:
        for title_form in title_forms:
            if name_form and name_form in title_form:
                score = max(score, 100)

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

    if any(
        form in title_form
        for variant in city_variants(city)
        for form in text_forms(variant)
        for title_form in title_forms
    ):
        score += 30

    if extra_words:
        type_words = [word for word in normalize_text(extra_words).split() if len(word) >= 4]
        if any(form in title_form for word in type_words for form in text_forms(word) for title_form in title_forms):
            score += 15

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

    if normalize_text(city) in ("брест", "брэст"):
        title_text = " ".join(title_forms)
        belarus_markers = ("belarus", "беларус", "brest belarus", "brest region", "брестская область", "брэсцкая")
        if not any(marker in title_text for marker in belarus_markers):
            score = min(score, 95)

    return score

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
    cleaned = PUNCT_RE.sub(" ", name)
    cleaned = INITIALS_RE.sub(" ", cleaned)
    tokens = [t.strip() for t in cleaned.split() if t.strip()]
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

    if type_word and proper_name:
        _add(f"{type_word} {proper_name} {be_city}")
        if ru_type and ru_proper:
            _add(f"{ru_type} {ru_proper} {ru_city}")
        _add(f"{type_word} {proper_name}")
        if ru_type and ru_proper:
            _add(f"{ru_type} {ru_proper}")

    _add(f"{clean_name} {be_city}")
    _add(f"{ru_name} {ru_city}")

    for oname in osm_names:
        _add(f"{oname} {ru_city}")
        _add(oname)

    _add(clean_name)
    _add(ru_name)

    if proper_name:
        _add(f"{proper_name} {be_city}")
        if ru_proper:
            _add(f"{ru_proper} {ru_city}")
        _add(proper_name)
        if ru_proper:
            _add(ru_proper)

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
