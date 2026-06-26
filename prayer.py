import httpx
from datetime import date

PRAYER_API = "https://api.aladhan.com/v1/timings/{date}"

PRAYER_NAMES = {
    "Fajr": "Фаджр",
    "Sunrise": "Восход",
    "Dhuhr": "Зухр",
    "Asr": "Аср",
    "Maghrib": "Магриб",
    "Isha": "Иша",
}

CITIES = {
    "москва":    {"lat": 55.7558, "lon": 37.6173, "tz": "Europe/Moscow"},
    "казань":    {"lat": 55.7879, "lon": 49.1233, "tz": "Europe/Moscow"},
    "уфа":       {"lat": 54.7348, "lon": 55.9579, "tz": "Asia/Yekaterinburg"},
    "махачкала": {"lat": 42.9849, "lon": 47.5047, "tz": "Europe/Moscow"},
    "грозный":   {"lat": 43.3178, "lon": 45.6949, "tz": "Europe/Moscow"},
    "астрахань": {"lat": 46.3498, "lon": 48.0408, "tz": "Europe/Astrakhan"},
    "самара":    {"lat": 53.1959, "lon": 50.1002, "tz": "Europe/Samara"},
    "челябинск": {"lat": 55.1600, "lon": 61.4000, "tz": "Asia/Yekaterinburg"},
    "омск":      {"lat": 54.9914, "lon": 73.3715, "tz": "Asia/Omsk"},
    "новосибирск":{"lat": 55.0084, "lon": 82.9357, "tz": "Asia/Novosibirsk"},
    "казань":    {"lat": 55.7879, "lon": 49.1233, "tz": "Europe/Moscow"},
    "с.-петербург":{"lat": 59.9311, "lon": 30.3609, "tz": "Europe/Moscow"},
    "спб":       {"lat": 59.9311, "lon": 30.3609, "tz": "Europe/Moscow"},
    "ташкент":   {"lat": 41.2995, "lon": 69.2401, "tz": "Asia/Tashkent"},
    "стамбул":   {"lat": 41.0082, "lon": 28.9784, "tz": "Europe/Istanbul"},
    "дубай":     {"lat": 25.2048, "lon": 55.2708, "tz": "Asia/Dubai"},
    "эр-рияд":   {"lat": 24.7136, "lon": 46.6753, "tz": "Asia/Riyadh"},
    "каир":      {"lat": 30.0444, "lon": 31.2357, "tz": "Africa/Cairo"},
    "лондон":    {"lat": 51.5074, "lon": -0.1278, "tz": "Europe/London"},
    "берлин":    {"lat": 52.5200, "lon": 13.4050, "tz": "Europe/Berlin"},
    "нью-йорк":  {"lat": 40.7128, "lon": -74.0060, "tz": "America/New_York"},
}


async def get_prayer_times(lat: float, lon: float, for_date: date = None) -> dict:
    if for_date is None:
        for_date = date.today()
    date_str = for_date.strftime("%d-%m-%Y")
    url = PRAYER_API.format(date=date_str)
    params = {"latitude": lat, "longitude": lon, "method": 2}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, timeout=15)
        data = resp.json()
    timings = data["data"]["timings"]
    result = {}
    for en_name, ru_name in PRAYER_NAMES.items():
        time_str = timings[en_name].split(" ")[0]
        result[ru_name] = time_str
    return result


async def get_prayer_message(lat: float, lon: float, city: str = "Москва") -> str:
    times = await get_prayer_times(lat, lon)
    lines = [f"🕌 *Время намазов — {city}:*\n"]
    for name, t in times.items():
        lines.append(f"  *{name}* — `{t}`")
    return "\n".join(lines)


def find_city(name: str) -> dict | None:
    key = name.strip().lower()
    return CITIES.get(key)
