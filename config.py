import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
PROXY_URL = os.getenv("PROXY_URL", "")
DEEZER_ARL = os.getenv("DEEZER_ARL", "")
TIMEZONE = "Europe/Moscow"
DB_PATH = os.getenv("DB_PATH", "music_bot.db")

# Deezer API (бесплатно, без ключа)
DEEZER_BASE_URL = "https://api.deezer.com"
DEEZER_SEARCH_LIMIT = 25

# YouTube (через yt-dlp)
YTDLP_PATH = os.getenv("YTDLP_PATH", "yt-dlp")

# Genius (скрейпинг, без ключа)
GENIUS_BASE_URL = "https://genius.com"

# LRCLIB (открытый API для текстов с таймкодами)
LRCLIB_BASE_URL = "https://lrclib.net/api"

# Лимиты
MAX_SEARCH_RESULTS = 10
MAX_FAVORITES = 500
MAX_PLAYLISTS = 20
MAX_PLAYLIST_TRACKS = 100
MAX_HISTORY = 50

# Временные звуки (секунды)
PREVIEW_DURATION = 30

# Языки
SUPPORTED_LANGUAGES = {
    "ru": "Русский",
    "en": "English",
    "uz": "O'zbek",
    "tg": "Тоҷикӣ",
}

DEFAULT_LANGUAGE = "ru"
