import asyncio
import logging
import os
import json
import glob as glob_mod
from config import YTDLP_PATH

logger = logging.getLogger(__name__)

TEMP_DIR = "temp_audio"


async def ensure_temp_dir():
    os.makedirs(TEMP_DIR, exist_ok=True)


async def search_and_download(query: str, track_id: int = 0) -> str | None:
    await ensure_temp_dir()
    output_template = os.path.join(TEMP_DIR, f"{track_id}_%(id)s.%(ext)s")

    cmd = [
        YTDLP_PATH,
        f"ytsearch1:{query}",
        "-x",
        "--audio-format", "mp3",
        "--audio-quality", "192K",
        "-o", output_template,
        "--no-playlist",
        "--no-warnings",
        "--socket-timeout", "30",
        "--retries", "3",
        "--no-check-certificates",
        "--extractor-args", "youtube:player_client=ios,android",
        "--user-agent", "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=90)

        if proc.returncode != 0:
            err = stderr.decode(errors="ignore")
            logger.error(f"yt-dlp error: {err[:500]}")
            return None

        mp3_files = glob_mod.glob(os.path.join(TEMP_DIR, f"{track_id}_*.mp3"))
        if mp3_files:
            latest = max(mp3_files, key=os.path.getmtime)
            size = os.path.getsize(latest)
            if size > 50000:
                return latest
            else:
                try:
                    os.remove(latest)
                except Exception:
                    pass
                return None

        all_mp3 = glob_mod.glob(os.path.join(TEMP_DIR, "*.mp3"))
        if all_mp3:
            latest = max(all_mp3, key=os.path.getmtime)
            size = os.path.getsize(latest)
            if size > 50000:
                return latest

        return None

    except asyncio.TimeoutError:
        logger.error("yt-dlp timeout")
        return None
    except FileNotFoundError:
        logger.error("yt-dlp not found")
        return None
    except Exception as e:
        logger.error(f"yt-dlp error: {e}")
        return None


async def search_youtube(query: str, limit: int = 5) -> list:
    await ensure_temp_dir()
    cmd = [
        YTDLP_PATH,
        f"ytsearch{limit}:{query}",
        "--flat-playlist",
        "--dump-json",
        "--no-warnings",
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        if proc.returncode != 0:
            return []
        results = []
        for line in stdout.decode().strip().split("\n"):
            if line.strip():
                try:
                    data = json.loads(line)
                    results.append({
                        "id": data.get("id", ""),
                        "title": data.get("title", ""),
                        "url": data.get("url") or data.get("webpage_url") or f"https://www.youtube.com/watch?v={data.get('id', '')}",
                        "duration": data.get("duration", 0),
                        "channel": data.get("channel") or data.get("uploader", ""),
                        "thumbnail": data.get("thumbnail", ""),
                    })
                except json.JSONDecodeError:
                    continue
        return results
    except Exception as e:
        logger.error(f"yt-dlp search error: {e}")
        return []


async def download_audio(url: str, output_path: str = None) -> str | None:
    await ensure_temp_dir()
    if not output_path:
        output_path = os.path.join(TEMP_DIR, "%(id)s.%(ext)s")
    cmd = [
        YTDLP_PATH,
        url,
        "-x",
        "--audio-format", "mp3",
        "--audio-quality", "192K",
        "-o", output_path,
        "--no-playlist",
        "--no-warnings",
        "--socket-timeout", "30",
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        if proc.returncode != 0:
            return None
        mp3_files = glob_mod.glob(os.path.join(TEMP_DIR, "*.mp3"))
        if mp3_files:
            return max(mp3_files, key=os.path.getmtime)
        return None
    except Exception as e:
        logger.error(f"yt-dlp download error: {e}")
        return None


def cleanup_temp():
    if os.path.exists(TEMP_DIR):
        for f in os.listdir(TEMP_DIR):
            fp = os.path.join(TEMP_DIR, f)
            try:
                os.remove(fp)
            except Exception:
                pass
