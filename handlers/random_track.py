import random
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

from database import get_user, get_listen_history, get_favorites
from deezer_api import get_chart, search_tracks, get_cover_url, format_duration
from translations import t

router = Router()

central_asian_artists = [
    "Rustam Azimi", "Bahrom Gafuri", "Shabnami Surayo",
    "Shabnam Surayo", "Bakhtiyor Ibrohimov", "Farhod Oripov",
    "Daler Ruz", "Otabek Mutalibov", "Sherali Jo'rayev",
    "Yulduz Usmonova", "Sardor Rahimhon", "Ozoda Nursaidova",
    "Nilufar Usmonova", "Shahzoda", "Rayhon",
]

western_artists = [
    "Eminem", "Drake", "The Weeknd", "Billie Eilish",
    "Adele", "Ed Sheeran", "Taylor Swift", "Bruno Mars",
    "Post Malone", "Daft Punk", "Arctic Monkeys",
    "Imagine Dragons", "Rihanna", "Beyonce", "SZA", "Dua Lipa",
]

russian_artists = [
    "Мумий Тролль", "Земфира", "Баста", "Скриптонит",
    "Кино", "Oxxxymiron", "Noize MC", "Rauf & Faik",
    "Jah Khalib", "Мот", "Звонкий",
]


@router.callback_query(F.data == "random_track")
async def cb_random_track(cb: CallbackQuery):
    user_id = cb.from_user.id

    history = await get_listen_history(user_id, limit=20)
    listened_ids = {h["track_id"] for h in history}

    all_tracks = []

    chart = await get_chart(limit=15)
    if chart:
        all_tracks.extend(chart)

    sample_artists = (
        random.sample(central_asian_artists, 3) +
        random.sample(western_artists, 2) +
        random.sample(russian_artists, 2)
    )
    random.shuffle(sample_artists)

    for artist in sample_artists[:6]:
        tracks = await search_tracks(artist, limit=5)
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

    random.shuffle(unlistened)
    selected = unlistened[:5]

    buttons = []
    for i, track in enumerate(selected, 1):
        title = track.get("title", "?")[:25]
        artist = track.get("artist", {}).get("name", "?")[:18]
        dur = format_duration(track.get("duration", 0))
        buttons.append([InlineKeyboardButton(
            text=f"{i}. {title} — {artist} ({dur})",
            callback_data=f"track_{track['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="🔄 Ещё", callback_data="random_track")])
    buttons.append([InlineKeyboardButton(text="🔙 Меню", callback_data="main_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    text = "🎲 <b>Случайные треки</b>\n\nТаджикская, узбекская и мировая музыка:\n"
    cover = get_cover_url(selected[0]) if selected else None
    if cover:
        try:
            await cb.message.delete()
            await cb.message.answer_photo(
                cover, caption=text, parse_mode=ParseMode.HTML, reply_markup=kb,
            )
            await cb.answer()
            return
        except Exception:
            pass

    await cb.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    await cb.answer()
