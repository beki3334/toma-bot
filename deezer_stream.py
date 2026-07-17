import deezer as deezer_lib
import requests
import logging
import time

logger = logging.getLogger(__name__)

_dz_instance = None
_arl = None
_url_cache = {}
_cache_ttl = 300  # 5 minutes


def init_deezer(arl: str):
    global _dz_instance, _arl
    _arl = arl
    _dz_instance = deezer_lib.Deezer()
    _dz_instance.login_via_arl(arl)
    logger.info(f"Deezer initialized, logged in: {_dz_instance.logged_in}")


def get_full_track_url(track_id: int) -> str | None:
    global _dz_instance

    cached = _url_cache.get(track_id)
    if cached and time.time() - cached["time"] < _cache_ttl:
        return cached["url"]

    if not _dz_instance or not _dz_instance.logged_in:
        return None

    try:
        license_token = _dz_instance.current_user.get("license_token", "")
        if not license_token:
            return None

        gw = _dz_instance.gw
        track = gw.get_track_with_fallback(track_id)
        if not track:
            return None

        track_token = track.get("TRACK_TOKEN", "")
        if not track_token:
            return None

        headers = _dz_instance.http_headers
        payload = {
            "license_token": license_token,
            "media": [{
                "type": "FULL",
                "formats": [
                    {"cipher": "BF_CBC_STRIPE", "format": "MP3_128"}
                ]
            }],
            "track_tokens": [track_token]
        }
        resp = requests.post(
            "https://media.deezer.com/v1/get_url",
            json=payload,
            headers=headers,
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            track_data = data.get("data", [{}])[0]
            media_list = track_data.get("media", [])
            if media_list:
                sources = media_list[0].get("sources", [])
                if sources:
                    url = sources[0].get("url")
                    if url:
                        _url_cache[track_id] = {"url": url, "time": time.time()}
                    return url
        return None
    except Exception as e:
        logger.error(f"Get full track URL error: {e}")
        return None


def is_deezer_ready() -> bool:
    return _dz_instance is not None and _dz_instance.logged_in
