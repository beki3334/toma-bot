import random
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.enums import ParseMode

from database import get_user, get_listen_history, get_favorites
from deezer_api import get_chart, search_tracks, get_cover_url, format_duration
from keyboards import track_actions_kb
from translations import t

router = Router()

random_queries = [
    "love", "dance", "chill", "rock", "pop", "hip hop", "r&b",
    "jazz", "classical", "electronic", "indie", "alternative",
    "Кино", "Мумий Тролль", "Земфира", "Баста", "Скриптонит",
    "Rihanna", "Drake", "The Weeknd", "Billie Eilish", "Adele",
    "Ed Sheeran", "Taylor Swift", "Bruno Mars", "Post Malone",
    "Daft Punk", "Arctic Monkeys", "Imagine Dragons",
]


@router.callback_query(F.data == "random_track")
async def cb_random_track(cb: CallbackQuery):
    user_id = cb.from_user.id
    lang = (await get_user(user_id) or {}).get("language", "ru")

    history = await get_listen_history(user_id, limit=10)
    listened_ids = {h["track_id"] for h in history}

    favs = await get_favorites(user_id, limit=10)
    fav_ids = {f["track_id"] for f in favs}

    tracks = await get_chart(limit=50)

    if not tracks:
        query = random.choice(random_queries)
        tracks = await search_tracks(query, limit=25)

    if not tracks:
        await cb.answer("Не удалось найти трек", show_alert=True)
        return

    filtered = [t for t in tracks if t["id"] not in listened_ids]
    if not filtered:
        filtered = tracks

    prefer = [t for t in filtered if t["id"] in fav_ids]
    if prefer and random.random() < 0.3:
        track = random.choice(prefer)
    else:
        track = random.choice(filtered)

    title = track.get("title", "?")
    artist = track.get("artist", {}).get("name", "?")
    duration = format_duration(track.get("duration", 0))
    cover = get_cover_url(track)

    text = (
        f"🎲 <b>Случайный трек</b>\n\n"
        f"🎵 <b>{title}</b>\n"
        f"👤 {artist}\n"
        f"⏱ {duration}"
    )
    kb = track_actions_kb(track["id"], False)

    if cover:
        try:
            await cb.message.delete()
            await cb.message.answer_photo(
                cover,
                caption=text,
                parse_mode=ParseMode.HTML,
                reply_markup=kb,
            )
            await cb.answer()
            return
        except Exception:
            pass

    await cb.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    await cb.answer()
