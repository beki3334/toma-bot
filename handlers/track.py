import os
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from database import (
    register_user, get_user, add_listen_history,
    add_favorite, remove_favorite, is_favorite,
    get_playlists,
)
from deezer import get_track, format_track_info, get_cover_url, format_duration
from keyboards import track_actions_kb, search_menu_kb, BACK_KB
from youtube import download_audio, cleanup_temp
from translations import t

logger = logging.getLogger(__name__)
router = Router()


class TrackStates(StatesGroup):
    waiting_new_playlist_name = State()


async def show_track_detail(message_or_cb, track_id: int, user_id: int, edit: bool = False):
    track = await get_track(track_id)
    if not track:
        text = "❌ Трек не найден."
        if edit:
            await message_or_cb.message.edit_text(text, reply_markup=BACK_KB)
        else:
            await message_or_cb.answer(text, reply_markup=BACK_KB)
        return

    await add_listen_history(user_id, track)
    in_fav = await is_favorite(user_id, track_id)

    lang = (await get_user(user_id) or {}).get("language", "ru")
    artist_name = track.get("artist", {}).get("name", "?")
    album_title = track.get("album", {}).get("title", "?")
    duration = format_duration(track.get("duration", 0))

    text = (
        f"🎵 <b>{track.get('title', '?')}</b>\n"
        f"👤 {artist_name}\n"
        f"💿 {album_title}\n"
        f"⏱ {duration}"
    )
    if track.get("explicit"):
        text += "\n🔞 Explicit"

    kb = track_actions_kb(track_id, in_fav)

    if edit:
        await message_or_cb.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        cover = get_cover_url(track)
        if cover:
            try:
                await message_or_cb.answer_photo(cover, caption=text, parse_mode=ParseMode.HTML, reply_markup=kb)
                return
            except Exception:
                pass
        if isinstance(message_or_cb, CallbackQuery):
            await message_or_cb.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        else:
            await message_or_cb.answer(text, parse_mode=ParseMode.HTML, reply_markup=kb)


@router.callback_query(F.data.startswith("track_"))
async def cb_track_detail(cb: CallbackQuery):
    track_id = int(cb.data.split("_")[1])
    await cb.answer()
    await show_track_detail(cb, track_id, cb.from_user.id, edit=True)


@router.callback_query(F.data.startswith("play_"))
async def cb_play_track(cb: CallbackQuery):
    track_id = int(cb.data.split("_")[1])
    track = await get_track(track_id)
    if not track:
        await cb.answer("Трек не найден", show_alert=True)
        return

    preview = track.get("preview")
    if not preview:
        await cb.answer("Превью недоступно", show_alert=True)
        return

    lang = (await get_user(cb.from_user.id) or {}).get("language", "ru")
    artist = track.get("artist", {}).get("name", "?")
    title = track.get("title", "?")

    try:
        import httpx
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(preview)
            if resp.status_code == 200:
                temp_path = f"temp_audio/{track_id}_preview.mp3"
                os.makedirs("temp_audio", exist_ok=True)
                with open(temp_path, "wb") as f:
                    f.write(resp.content)
                await cb.message.answer_audio(
                    FSInputFile(temp_path),
                    title=title,
                    performer=artist,
                    caption=f"▶️ {t(cb.from_user.id, 'playing', lang, title=title, artist=artist)}",
                )
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            else:
                await cb.answer("Ошибка загрузки превью", show_alert=True)
    except Exception as e:
        logger.error(f"Play error: {e}")
        await cb.answer("Ошибка воспроизведения", show_alert=True)


@router.callback_query(F.data.startswith("download_"))
async def cb_download_track(cb: CallbackQuery):
    track_id = int(cb.data.split("_")[1])
    track = await get_track(track_id)
    if not track:
        await cb.answer("Трек не найден", show_alert=True)
        return

    lang = (await get_user(cb.from_user.id) or {}).get("language", "ru")
    artist = track.get("artist", {}).get("name", "?")
    title = track.get("title", "?")

    preview = track.get("preview")
    if not preview:
        await cb.answer("Аудио недоступно", show_alert=True)
        return

    await cb.answer(t(cb.from_user.id, "processing", lang))
    try:
        import httpx
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(preview)
            if resp.status_code == 200:
                temp_path = f"temp_audio/{track_id}_download.mp3"
                os.makedirs("temp_audio", exist_ok=True)
                with open(temp_path, "wb") as f:
                    f.write(resp.content)
                await cb.message.answer_audio(
                    FSInputFile(temp_path),
                    title=title,
                    performer=artist,
                    caption=f"📥 {title} — {artist}\n\n⚠️ 30-секундное превью (Deezer)",
                )
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            else:
                await cb.message.answer(t(cb.from_user.id, "download_error", lang))
    except Exception as e:
        logger.error(f"Download error: {e}")
        await cb.message.answer(t(cb.from_user.id, "download_error", lang))


@router.callback_query(F.data.startswith("fav_"))
async def cb_add_favorite(cb: CallbackQuery):
    track_id = int(cb.data.split("_")[1])
    track = await get_track(track_id)
    if not track:
        await cb.answer("Трек не найден", show_alert=True)
        return
    added = await add_favorite(cb.from_user.id, track)
    lang = (await get_user(cb.from_user.id) or {}).get("language", "ru")
    if added:
        await cb.answer(t(cb.from_user.id, "added_to_favorites", lang), show_alert=True)
    else:
        await cb.answer("Уже в избранном или лимит Reached", show_alert=True)

    in_fav = await is_favorite(cb.from_user.id, track_id)
    await cb.message.edit_reply_markup(reply_markup=track_actions_kb(track_id, in_fav))


@router.callback_query(F.data.startswith("unfav_"))
async def cb_remove_favorite(cb: CallbackQuery):
    track_id = int(cb.data.split("_")[1])
    removed = await remove_favorite(cb.from_user.id, track_id)
    lang = (await get_user(cb.from_user.id) or {}).get("language", "ru")
    if removed:
        await cb.answer(t(cb.from_user.id, "removed_from_favorites", lang), show_alert=True)
    else:
        await cb.answer("Не найдено", show_alert=True)

    in_fav = await is_favorite(cb.from_user.id, track_id)
    await cb.message.edit_reply_markup(reply_markup=track_actions_kb(track_id, in_fav))


@router.callback_query(F.data.startswith("artist_from_track_"))
async def cb_artist_from_track(cb: CallbackQuery):
    track_id = int(cb.data.split("_")[-1])
    track = await get_track(track_id)
    if not track:
        await cb.answer("Не найдено", show_alert=True)
        return
    from handlers.artist import show_artist_detail
    artist_id = track.get("artist", {}).get("id")
    if artist_id:
        await cb.answer()
        await show_artist_detail(cb, artist_id, cb.from_user.id)
    else:
        await cb.answer("Исполнитель не найден", show_alert=True)


@router.callback_query(F.data.startswith("album_from_track_"))
async def cb_album_from_track(cb: CallbackQuery):
    track_id = int(cb.data.split("_")[-1])
    track = await get_track(track_id)
    if not track:
        await cb.answer("Не найдено", show_alert=True)
        return
    from handlers.album import show_album_detail
    album_id = track.get("album", {}).get("id")
    if album_id:
        await cb.answer()
        await show_album_detail(cb, album_id, cb.from_user.id)
    else:
        await cb.answer("Альбом не найден", show_alert=True)


@router.callback_query(F.data == "back_from_track")
async def cb_back_from_track(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    from handlers.search import search_cache
    cache = search_cache.get(cb.from_user.id)
    if cache and cache.get("results"):
        from keyboards import search_results_kb
        lang = (await get_user(cb.from_user.id) or {}).get("language", "ru")
        text = f"🔍 <b>Результаты поиска:</b>\n\nЗапрос: <i>{cache['query']}</i>"
        await cb.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=search_results_kb(cache["results"], cache["type"], page=0),
        )
    else:
        from keyboards import main_menu_kb
        lang = (await get_user(cb.from_user.id) or {}).get("language", "ru")
        await cb.message.edit_text(
            t(cb.from_user.id, "main_menu", lang),
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_kb(),
        )
    await cb.answer()
