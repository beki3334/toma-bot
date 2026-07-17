from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.enums import ParseMode

from database import get_user
from deezer_api import get_artist, get_artist_top_tracks, get_artist_albums, get_cover_url, format_duration
from keyboards import artist_kb, BACK_KB
from translations import t

router = Router()


async def show_artist_detail(message_or_cb, artist_id: int, user_id: int, edit: bool = False):
    artist = await get_artist(artist_id)
    if not artist:
        text = "❌ Исполнитель не найден."
        if edit:
            await message_or_cb.message.edit_text(text, reply_markup=BACK_KB)
        else:
            await message_or_cb.answer(text)
        return

    lang = (await get_user(user_id) or {}).get("language", "ru")
    name = artist.get("name", "?")
    nb_track = artist.get("nb_album", 0)
    nb_fan = artist.get("nb_fan", 0)

    text = (
        f"👤 <b>{name}</b>\n\n"
        f"🎵 Треков: ~{nb_track * 10}\n"
        f"💿 Альбомов: {nb_track}\n"
        f"❤️ Фанатов: {nb_fan:,}"
    )
    if artist.get("radio"):
        text += "\n📻 Есть радиостанция"

    kb = artist_kb(artist_id, name)
    cover = artist.get("picture_xl") or artist.get("picture_big") or artist.get("picture_medium", "")

    if cover:
        try:
            if edit:
                await message_or_cb.message.delete()
            await message_or_cb.message.answer_photo(
                cover,
                caption=text,
                parse_mode=ParseMode.HTML,
                reply_markup=kb,
            )
            return
        except Exception:
            pass

    if edit:
        await message_or_cb.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await message_or_cb.answer(text, parse_mode=ParseMode.HTML, reply_markup=kb)


@router.callback_query(F.data.startswith("artist_"))
async def cb_artist_detail(cb: CallbackQuery):
    parts = cb.data.split("_")
    artist_id = int(parts[1])
    await cb.answer()
    await show_artist_detail(cb, artist_id, cb.from_user.id, edit=True)


@router.callback_query(F.data.startswith("artist_top_"))
async def cb_artist_top(cb: CallbackQuery):
    artist_id = int(cb.data.split("_")[2])
    tracks = await get_artist_top_tracks(artist_id, limit=10)
    artist = await get_artist(artist_id)
    if not tracks:
        await cb.answer("Нет треков", show_alert=True)
        return

    lang = (await get_user(cb.from_user.id) or {}).get("language", "ru")
    name = artist.get("name", "?") if artist else "?"

    lines = [f"🎵 <b>Топ треков — {name}</b>\n"]
    for i, t in enumerate(tracks, 1):
        title = t.get("title", "?")
        duration = format_duration(t.get("duration", 0))
        lines.append(f"{i}. {title} — {duration}")

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    buttons = []
    for t in tracks[:10]:
        buttons.append([InlineKeyboardButton(
            text=f"▶️ {t.get('title', '?')[:35]}",
            callback_data=f"track_{t['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"artist_{artist_id}")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await cb.message.edit_text("\n".join(lines), parse_mode=ParseMode.HTML, reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.startswith("artist_albums_"))
async def cb_artist_albums(cb: CallbackQuery):
    artist_id = int(cb.data.split("_")[2])
    albums = await get_artist_albums(artist_id, limit=10)
    artist = await get_artist(artist_id)
    if not albums:
        await cb.answer("Нет альбомов", show_alert=True)
        return

    name = artist.get("name", "?") if artist else "?"
    lines = [f"💿 <b>Альбомы — {name}</b>\n"]
    for i, a in enumerate(albums, 1):
        title = a.get("title", "?")
        year = a.get("release_date", "?")[:4]
        lines.append(f"{i}. {title} ({year})")

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    buttons = []
    for a in albums[:10]:
        buttons.append([InlineKeyboardButton(
            text=f"💿 {a.get('title', '?')[:35]}",
            callback_data=f"album_{a['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"artist_{artist_id}")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await cb.message.edit_text("\n".join(lines), parse_mode=ParseMode.HTML, reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data == "back_from_artist")
async def cb_back_from_artist(cb: CallbackQuery):
    from keyboards import main_menu_kb
    lang = (await get_user(cb.from_user.id) or {}).get("language", "ru")
    from translations import t as tr
    await cb.message.edit_text(
        tr(cb.from_user.id, "main_menu", lang),
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_kb(),
    )
    await cb.answer()
