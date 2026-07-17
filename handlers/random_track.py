import random
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

from database import get_user, get_listen_history, get_favorites
from deezer_api import get_chart, search_tracks, get_cover_url, format_duration, get_track
from translations import t

router = Router()

random_queries = [
    ("Eminem", "en"), ("Drake", "en"), ("The Weeknd", "en"),
    ("Billie Eilish", "en"), ("Adele", "en"), ("Ed Sheeran", "en"),
    ("Taylor Swift", "en"), ("Bruno Mars", "en"), ("Post Malone", "en"),
    ("Daft Punk", "en"), ("Arctic Monkeys", "en"), ("Imagine Dragons", "en"),
    ("Rihanna", "en"), ("Beyonce", "en"), ("Kendrick Lamar", "en"),
    ("The Weeknd", "en"), ("SZA", "en"), ("Dua Lipa", "en"),
    ("Мумий Тролль", "ru"), ("Земфира", "ru"), ("Баста", "ru"),
    ("Скриптонит", "ru"), ("Кино", "ru"), ("Oxxxymiron", "ru"),
    ("Noize MC", "ru"), ("Звонкий", "ru"), ("Мот", "ru"),
    ("Rauf & Faik", "ru"), ("Jah Khalib", "ru"),
    ("Shazam", "tr"), ("Måneskin", "it"), ("Rosalía", "es"),
    ("Blackpink", "ko"), ("BTS", "ko"), ("Bad Bunny", "es"),
]


@router.callback_query(F.data == "random_track")
async def cb_random_track(cb: CallbackQuery):
    user_id = cb.from_user.id

    history = await get_listen_history(user_id, limit=20)
    listened_ids = {h["track_id"] for h in history}

    favs = await get_favorites(user_id, limit=20)
    fav_ids = {f["track_id"] for f in favs}

    all_tracks = []

    chart = await get_chart(limit=25)
    if chart:
        all_tracks.extend(chart)

    selected_artists = random.sample(random_queries, min(4, len(random_queries)))
    for artist_name, lang in selected_artists:
        tracks = await search_tracks(artist_name, limit=5)
        if tracks:
            all_tracks.extend(tracks)

    if not all_tracks:
        await cb.answer("Не удалось загрузить треки", show_alert=True)
        return

    unique_tracks = {t["id"]: t for t in all_tracks}
    all_tracks = list(unique_tracks.values())

    unlistened = [t for t in all_tracks if t["id"] not in listened_ids]
    if len(unlistened) < 5:
        unlistened = all_tracks

    preferred = [t for t in unlistened if t["id"] in fav_ids]
    if len(preferred) >= 3:
        pool = preferred
    else:
        pool = unlistened

    random.shuffle(pool)
    selected = pool[:5]

    text = "🎲 <b>Случайные треки</b>\n\nВыбери что послушать:\n"
    buttons = []
    for i, track in enumerate(selected, 1):
        title = track.get("title", "?")[:28]
        artist = track.get("artist", {}).get("name", "?")[:20]
        dur = format_duration(track.get("duration", 0))
        buttons.append([InlineKeyboardButton(
            text=f"{i}. {title} — {artist} ({dur})",
            callback_data=f"track_{track['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="🔄 Ещё", callback_data="random_track")])
    buttons.append([InlineKeyboardButton(text="🔙 Меню", callback_data="main_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    cover = get_cover_url(selected[0]) if selected else None
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
