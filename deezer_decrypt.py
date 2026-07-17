import hashlib
import requests
from Cryptodome.Cipher import Blowfish

CHUNK_SIZE = 2048
IV = b"\x00\x01\x02\x03\x04\x05\x06\x07"


def generate_blowfish_key(track_id: int) -> bytes:
    SECRET = 'g4el58wc0zvf9na1'
    id_md5 = hashlib.md5(str(track_id).encode()).hexdigest()
    bf_key = ""
    for i in range(16):
        bf_key += chr(ord(id_md5[i]) ^ ord(id_md5[i + 16]) ^ ord(SECRET[i]))
    return bf_key.encode()


def decrypt_chunk(key: bytes, data: bytes) -> bytes:
    cipher = Blowfish.new(key, Blowfish.MODE_CBC, IV)
    return cipher.decrypt(data)


def decrypt_deezer_stream(stream_data: bytes, track_id: int) -> bytes:
    key = generate_blowfish_key(track_id)
    decrypted = b""
    pos = 0

    while pos < len(stream_data):
        chunk = stream_data[pos:pos + CHUNK_SIZE]
        pos += CHUNK_SIZE

        if len(chunk) >= CHUNK_SIZE:
            decrypted += decrypt_chunk(key, chunk[:CHUNK_SIZE])
            decrypted += chunk[CHUNK_SIZE:]
        else:
            decrypted += chunk

    return decrypted


def download_and_decrypt(track_id: int, arl: str, output_path: str) -> bool:
    import deezer as deezer_lib

    dz = deezer_lib.Deezer()
    dz.login_via_arl(arl)

    if not dz.logged_in:
        return False

    try:
        gw = dz.gw
        track_info = gw.get_track_with_fallback(track_id)
        if not track_info:
            return False

        license_token = dz.current_user.get("license_token", "")
        track_token = track_info.get("TRACK_TOKEN", "")
        if not license_token or not track_token:
            return False

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
            headers=dz.http_headers,
            timeout=15
        )
        if resp.status_code != 200:
            return False

        data = resp.json()
        media = data.get("data", [{}])[0].get("media", [])
        if not media:
            return False

        stream_url = media[0].get("sources", [{}])[0].get("url")
        if not stream_url:
            return False

        audio_resp = requests.get(
            stream_url,
            timeout=30,
            headers={"User-Agent": "Deezer/7.0.0"}
        )
        if audio_resp.status_code != 200:
            return False

        encrypted_data = audio_resp.content
        if len(encrypted_data) < 1000:
            return False

        decrypted = decrypt_deezer_stream(encrypted_data, track_id)

        if len(decrypted) > 1000:
            with open(output_path, "wb") as f:
                f.write(decrypted)
            return True

        return False

    except Exception as e:
        print(f"Download error: {e}")
        return False
