import asyncio
import logging
import os
import json
from config import YTDLP_PATH

logger = logging.getLogger(__name__)

TEMP_DIR = "temp_audio"


async def ensure_temp_dir():
    os.makedirs(TEMP_DIR, exist_ok=True)


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
            logger.error(f"yt-dlp search error: {stderr.decode()}")
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
    except asyncio.TimeoutError:
        logger.error("yt-dlp search timeout")
        return []
    except FileNotFoundError:
        logger.error("yt-dlp not found")
        return []
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
            logger.error(f"yt-dlp download error: {stderr.decode()}")
            return None
        output = stdout.decode()
        for line in output.split("\n"):
            if "[ExtractAudio]" in line or "has already been downloaded" in line:
                pass
        mp3_files = []
        for f in os.listdir(TEMP_DIR):
            if f.endswith(".mp3"):
                mp3_files.append(os.path.join(TEMP_DIR, f))
        if mp3_files:
            latest = max(mp3_files, key=os.path.getmtime)
            return latest
        return None
    except asyncio.TimeoutError:
        logger.error("yt-dlp download timeout")
        return None
    except FileNotFoundError:
        logger.error("yt-dlp not found")
        return None
    except Exception as e:
        logger.error(f"yt-dlp download error: {e}")
        return None


async def get_video_info(url: str) -> dict | None:
    cmd = [
        YTDLP_PATH,
        url,
        "--dump-json",
        "--no-download",
        "--no-warnings",
        "--socket-timeout", "15",
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        if proc.returncode != 0:
            return None
        return json.loads(stdout.decode())
    except Exception as e:
        logger.error(f"yt-dlp info error: {e}")
        return None


def cleanup_temp():
    if os.path.exists(TEMP_DIR):
        for f in os.listdir(TEMP_DIR):
            fp = os.path.join(TEMP_DIR, f)
            try:
                os.remove(fp)
            except Exception:
                pass
