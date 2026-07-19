import os
from pathlib import Path
from dotenv import load_dotenv
from src.utils.utils import info, log, error

BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / '.env'

load_dotenv(dotenv_path=env_path)


raw_token = os.getenv("BOT_TOKEN") or os.getenv("TOKEN")

if not raw_token:
    raise ValueError(f"❌ Ошибка: Токен бота не найден в {env_path}")


TOKEN = raw_token.strip().strip("'\"")


masked_token = f"{TOKEN[:6]}...{TOKEN[-4:]}" if len(TOKEN) > 10 else "Слишком короткий"
info(f"ℹ️ [Config] Успешно загружен токен (длина: {len(TOKEN)}, маска: {masked_token})")


DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "jarvis_db")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))


overpass_raw = os.getenv("OVERPASS_URLS", "")
if overpass_raw:
    OVERPASS_URLS = [url.strip() for url in overpass_raw.split(",") if url.strip()]
else:
    OVERPASS_URLS = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.openstreetmap.ru/api/interpreter"
    ]

DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "ru").strip().lower()

super_admins_raw = os.getenv("SUPER_ADMINS", "")
if super_admins_raw:
    SUPERADMINS = [int(x.strip()) for x in super_admins_raw.split(",") if x.strip().isdigit()]
else:
    SUPERADMINS = []

REGIONS = {
    "Минская область": ["Минск", "Борисов", "Солигорск", "Молодечно"],
    "Брестская область": ["Брест", "Барановичи", "Пинск", "Кобрин"],
    "Витебская область": ["Витебск", "Орша", "Полоцк", "Новополоцк"],
    "Гомельская область": ["Гомель", "Мозырь", "Жлобин", "Речица"],
    "Гродненская область": ["Гродно", "Лида", "Волковыск", "Сморгонь"],
    "Могилевская область": ["Могилев", "Бобруйск", "Горки", "Осиповичи"]
}

LIMITS = {
    "Минск": 300,
    "Брест": 20,
    "Гродно": 20
}

DEFAULT_LIMIT = int(os.getenv("DEFAULT_LIMIT", 15))