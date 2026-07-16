from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.enums import ParseMode

from database import get_user
from deezer import get_track
from lyrics import get_lyrics, format_lyrics
from keyboards import track_actions_kb, BACK_KB
from translations import t

router = Router()


@router.callback_query(F.data.startswith("lyrics_"))
async def cb_lyrics(cb: CallbackQuery):
    track_id = int(cb.data.split("_")[1])
    track = await get_track(track_id)
    if not track:
        await cb.answer("Трек не найден", show_alert=True)
        return

    lang = (await get_user(cb.from_user.id) or {}).get("language", "ru")
    title = track.get("title", "?")
    artist = track.get("artist", {}).get("name", "?")
    duration = track.get("duration", 0)

    await cb.answer(t(cb.from_user.id, "processing", lang))

    lyrics = await get_lyrics(title, artist, duration)
    if not lyrics or (not lyrics.get("plain") and not lyrics.get("synced")):
        text = (
            f"🎵 <b>{title}</b> — {artist}\n\n"
            f"{t(cb.from_user.id, 'lyrics_not_found', lang)}"
        )
        await cb.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=BACK_KB)
        return

    formatted = format_lyrics(lyrics)
    header = f"🎵 <b>{title}</b> — {artist}\n\n"
    full_text = header + formatted

    if len(full_text) > 4000:
        full_text = full_text[:4000] + "\n\n... (обрезано)"

    in_fav = False
    try:
        from database import is_favorite
        in_fav = await is_favorite(cb.from_user.id, track_id)
    except Exception:
        pass

    kb = track_actions_kb(track_id, in_fav)
    await cb.message.edit_text(full_text, parse_mode=ParseMode.HTML, reply_markup=kb)
