import httpx
import re
import logging
from config import GENIUS_BASE_URL, LRCLIB_BASE_URL

logger = logging.getLogger(__name__)


async def get_lyrics_from_lrclib(track_title: str, artist_name: str, duration: int = 0) -> dict | None:
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            params = {"track_name": track_title, "artist_name": artist_name}
            if duration:
                params["duration"] = duration
            resp = await client.get(f"{LRCLIB_BASE_URL}/get", params=params)
            if resp.status_code == 200:
                data = resp.json()
                synced = data.get("syncedLyrics")
                plain = data.get("plainLyrics")
                if synced or plain:
                    return {"synced": synced, "plain": plain, "source": "LRCLIB"}
        except Exception as e:
            logger.debug(f"LRCLIB error: {e}")

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(f"{LRCLIB_BASE_URL}/search", params={
                "track_name": track_title,
                "artist_name": artist_name,
            })
            if resp.status_code == 200:
                results = resp.json()
                for r in results[:3]:
                    synced = r.get("syncedLyrics")
                    plain = r.get("plainLyrics")
                    if synced or plain:
                        return {"synced": synced, "plain": plain, "source": "LRCLIB"}
        except Exception as e:
            logger.debug(f"LRCLIB search error: {e}")

    return None


async def get_lyrics_from_genius(track_title: str, artist_name: str) -> str | None:
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        try:
            search_url = f"{GENIUS_BASE_URL}/api/search"
            resp = await client.get(search_url, params={"q": f"{artist_name} {track_title}"})
            if resp.status_code != 200:
                return None

            html = resp.text
            song_paths = re.findall(r'data-api_path="(/songs/\d+)"', html)
            if not song_paths:
                song_paths = re.findall(r'"(/songs/\d+)"', html)
            if not song_paths:
                return None

            song_path = song_paths[0]
            song_resp = await client.get(f"{GENIUS_BASE_URL}{song_path}")
            if song_resp.status_code != 200:
                return None

            song_html = song_resp.text
            lyrics_match = re.search(
                r'<div[^>]*data-lyrics-container="true"[^>]*>(.*?)</div>',
                song_html, re.DOTALL
            )
            if not lyrics_match:
                lyrics_match = re.search(
                    r'<div[^>]*class="[^"]*Lyrics__Container[^"]*"[^>]*>(.*?)</div>',
                    song_html, re.DOTALL
                )
            if lyrics_match:
                lyrics = lyrics_match.group(1)
                lyrics = re.sub(r'<br\s*/?>', '\n', lyrics)
                lyrics = re.sub(r'<[^>]+>', '', lyrics)
                lyrics = lyrics.strip()
                if lyrics:
                    return lyrics

        except Exception as e:
            logger.debug(f"Genius scraping error: {e}")

    return None


async def get_lyrics(track_title: str, artist_name: str, duration: int = 0) -> dict | None:
    lrclib_result = await get_lyrics_from_lrclib(track_title, artist_name, duration)
    if lrclib_result:
        return lrclib_result

    genius_text = await get_lyrics_from_genius(track_title, artist_name)
    if genius_text:
        return {"synced": None, "plain": genius_text, "source": "Genius"}

    return None


def format_lyrics(lyrics: dict, max_length: int = 4000) -> str:
    if not lyrics:
        return ""

    synced = lyrics.get("synced")
    plain = lyrics.get("plain")
    source = lyrics.get("source", "")

    if synced:
        lines = []
        for line in synced.split("\n"):
            match = re.match(r'\[(\d+:\d+\.\d+)\]\s*(.*)', line)
            if match:
                time, text = match.groups()
                if text.strip():
                    lines.append(f"⏰ {time} {text}")
            else:
                lines.append(line)
        text = "\n".join(lines)
    elif plain:
        text = plain
    else:
        return ""

    if len(text) > max_length:
        text = text[:max_length] + "\n\n... (обрезано)"

    source_text = f"\n\n📖 Источник: {source}" if source else ""
    return text + source_text
