import httpx
import logging
from config import DEEZER_BASE_URL, DEEZER_SEARCH_LIMIT

logger = logging.getLogger(__name__)


async def search_tracks(query: str, limit: int = DEEZER_SEARCH_LIMIT) -> list:
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(f"{DEEZER_BASE_URL}/search", params={"q": query, "limit": limit})
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", [])
        except Exception as e:
            logger.error(f"Deezer search error: {e}")
            return []


async def search_artists(query: str, limit: int = 10) -> list:
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(f"{DEEZER_BASE_URL}/search/artist", params={"q": query, "limit": limit})
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", [])
        except Exception as e:
            logger.error(f"Deezer artist search error: {e}")
            return []


async def search_albums(query: str, limit: int = 10) -> list:
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(f"{DEEZER_BASE_URL}/search/album", params={"q": query, "limit": limit})
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", [])
        except Exception as e:
            logger.error(f"Deezer album search error: {e}")
            return []


async def get_track(track_id: int) -> dict | None:
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(f"{DEEZER_BASE_URL}/track/{track_id}")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Deezer track error: {e}")
            return None


async def get_artist(artist_id: int) -> dict | None:
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(f"{DEEZER_BASE_URL}/artist/{artist_id}")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Deezer artist error: {e}")
            return None


async def get_artist_top_tracks(artist_id: int, limit: int = 10) -> list:
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(f"{DEEZER_BASE_URL}/artist/{artist_id}/top", params={"limit": limit})
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", [])
        except Exception as e:
            logger.error(f"Deezer artist top error: {e}")
            return []


async def get_artist_albums(artist_id: int, limit: int = 10) -> list:
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(f"{DEEZER_BASE_URL}/artist/{artist_id}/albums", params={"limit": limit})
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", [])
        except Exception as e:
            logger.error(f"Deezer artist albums error: {e}")
            return []


async def get_album(album_id: int) -> dict | None:
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(f"{DEEZER_BASE_URL}/album/{album_id}")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Deezer album error: {e}")
            return None


async def get_album_tracks(album_id: int, limit: int = 50) -> list:
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(f"{DEEZER_BASE_URL}/album/{album_id}/tracks", params={"limit": limit})
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", [])
        except Exception as e:
            logger.error(f"Deezer album tracks error: {e}")
            return []


async def get_chart(limit: int = 25) -> list:
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(f"{DEEZER_BASE_URL}/chart/0/tracks", params={"limit": limit})
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", [])
        except Exception as e:
            logger.error(f"Deezer chart error: {e}")
            return []


async def get_radio() -> list:
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(f"{DEEZER_BASE_URL}/radio")
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", [])
        except Exception as e:
            logger.error(f"Deezer radio error: {e}")
            return []


async def search_lyrics(query: str) -> list:
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(f"{DEEZER_BASE_URL}/search/track", params={"q": query, "limit": 5})
            resp.raise_for_status()
            data = resp.json()
            tracks = data.get("data", [])
            results = []
            for t in tracks:
                if t.get("lyrics_id") and t["lyrics_id"] != 0:
                    results.append(t)
            return results
        except Exception as e:
            logger.error(f"Deezer lyrics search error: {e}")
            return []


def format_duration(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}"


def format_track_info(track: dict, short: bool = False) -> str:
    title = track.get("title", "Unknown")
    artist = track.get("artist", {}).get("name", "Unknown")
    album = track.get("album", {}).get("title", "")
    duration = format_duration(track.get("duration", 0))
    if short:
        return f"🎵 {title} — {artist}"
    lines = [
        f"🎵 <b>{title}</b>",
        f"👤 {artist}",
    ]
    if album:
        lines.append(f"💿 {album}")
    lines.append(f"⏱ {duration}")
    return "\n".join(lines)


def get_cover_url(track: dict, size: str = "xl") -> str:
    album = track.get("album", {})
    for key in [f"cover_{size}", "cover_big", "cover_medium", "cover_small"]:
        url = album.get(key)
        if url:
            return url
    return ""
