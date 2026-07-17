from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

from database import get_user, get_playlists, add_track_to_playlist
from deezer_api import get_album, get_album_tracks, get_cover_url, format_duration
from keyboards import album_kb, BACK_KB
from translations import t

router = Router()


async def show_album_detail(message_or_cb, album_id: int, user_id: int, edit: bool = False):
    album = await get_album(album_id)
    if not album:
        text = "❌ Альбом не найден."
        if edit:
            await message_or_cb.message.edit_text(text, reply_markup=BACK_KB)
        else:
            await message_or_cb.answer(text)
        return

    lang = (await get_user(user_id) or {}).get("language", "ru")
    title = album.get("title", "?")
    artist = album.get("artist", {}).get("name", "?")
    nb_tracks = album.get("nb_tracks", 0)
    duration = format_duration(album.get("duration", 0))
    release = album.get("release_date", "?")[:4]

    text = (
        f"💿 <b>{title}</b>\n"
        f"👤 {artist}\n"
        f"🎵 Треков: {nb_tracks}\n"
        f"⏱ {duration}\n"
        f"📅 {release}"
    )
    if album.get("explicit_lyrics"):
        text += "\n🔞 Explicit"

    kb = album_kb(album_id, title)
    cover = album.get("cover_xl") or album.get("cover_big") or album.get("cover_medium", "")

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


@router.callback_query(F.data.startswith("album_"))
async def cb_album_detail(cb: CallbackQuery):
    parts = cb.data.split("_")
    album_id = int(parts[1])
    await cb.answer()
    await show_album_detail(cb, album_id, cb.from_user.id, edit=True)


@router.callback_query(F.data.startswith("album_tracks_"))
async def cb_album_tracks(cb: CallbackQuery):
    album_id = int(cb.data.split("_")[2])
    tracks = await get_album_tracks(album_id)
    album = await get_album(album_id)
    if not tracks:
        await cb.answer("Нет треков", show_alert=True)
        return

    name = album.get("title", "?") if album else "?"
    artist = album.get("artist", {}).get("name", "?") if album else "?"

    lines = [f"💿 <b>{name}</b> — {artist}\n"]
    for i, t in enumerate(tracks, 1):
        title = t.get("title", "?")
        duration = format_duration(t.get("duration", 0))
        explicit = "🔞" if t.get("explicit_lyrics") else ""
        lines.append(f"{i}. {title} {explicit} — {duration}")

    buttons = []
    for t in tracks[:50]:
        buttons.append([InlineKeyboardButton(
            text=f"🎵 {t.get('title', '?')[:35]}",
            callback_data=f"track_{t['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"album_{album_id}")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await cb.message.edit_text("\n".join(lines), parse_mode=ParseMode.HTML, reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.startswith("artist_from_album_"))
async def cb_artist_from_album(cb: CallbackQuery):
    album_id = int(cb.data.split("_")[-1])
    album = await get_album(album_id)
    if not album:
        await cb.answer("Не найдено", show_alert=True)
        return
    from handlers.artist import show_artist_detail
    artist_id = album.get("artist", {}).get("id")
    if artist_id:
        await cb.answer()
        await show_artist_detail(cb, artist_id, cb.from_user.id)
    else:
        await cb.answer("Исполнитель не найден", show_alert=True)


@router.callback_query(F.data == "back_from_album")
async def cb_back_from_album(cb: CallbackQuery):
    from keyboards import main_menu_kb
    lang = (await get_user(cb.from_user.id) or {}).get("language", "ru")
    from translations import t as tr
    is_photo = cb.message.photo or (cb.message.caption and not cb.message.text)
    if is_photo:
        await cb.message.delete()
        await cb.message.answer(
            tr(cb.from_user.id, "main_menu", lang),
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_kb(),
        )
    else:
        await cb.message.edit_text(
            tr(cb.from_user.id, "main_menu", lang),
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_kb(),
        )
    await cb.answer()
