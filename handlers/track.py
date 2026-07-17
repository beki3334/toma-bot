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
from deezer_api import get_track, format_track_info, get_cover_url, format_duration
from keyboards import track_actions_kb, search_menu_kb, BACK_KB
from youtube import search_and_download, cleanup_temp
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

    import asyncio
    fav_task = asyncio.create_task(is_favorite(user_id, track_id))
    hist_task = asyncio.create_task(add_listen_history(user_id, track))

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
        text += " 🔞"

    in_fav = await fav_task
    kb = track_actions_kb(track_id, in_fav)

    if edit:
        await message_or_cb.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        cover = get_cover_url(track)
        if cover:
            try:
                await message_or_cb.answer_photo(cover, caption=text, parse_mode=ParseMode.HTML, reply_markup=kb)
                await hist_task
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


async def _download_track(track_id: int, track: dict) -> str | None:
    os.makedirs("temp_audio", exist_ok=True)

    from deezer_stream import get_full_track_url, is_deezer_ready
    if is_deezer_ready():
        import asyncio
        stream_url = await asyncio.to_thread(get_full_track_url, track_id)
        if stream_url:
            try:
                import httpx
                async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                    resp = await client.get(stream_url)
                    if resp.status_code == 200 and len(resp.content) > 50000:
                        path = f"temp_audio/{track_id}_full.mp3"
                        with open(path, "wb") as f:
                            f.write(resp.content)
                        return path
            except Exception as e:
                logger.error(f"Full track download error: {e}")

    preview = track.get("preview")
    if preview:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(preview)
                if resp.status_code == 200:
                    path = f"temp_audio/{track_id}_preview.mp3"
                    with open(path, "wb") as f:
                        f.write(resp.content)
                    return path
        except Exception as e:
            logger.error(f"Preview download error: {e}")

    return None


@router.callback_query(F.data.startswith("play_"))
async def cb_play_track(cb: CallbackQuery):
    track_id = int(cb.data.split("_")[1])
    track = await get_track(track_id)
    if not track:
        await cb.answer("Трек не найден", show_alert=True)
        return

    lang = (await get_user(cb.from_user.id) or {}).get("language", "ru")
    artist = track.get("artist", {}).get("name", "?")
    title = track.get("title", "?")

    await cb.answer(t(cb.from_user.id, "processing", lang))
    status_msg = await cb.message.answer(f"▶️ Загружаю: <b>{title}</b> — {artist}...", parse_mode=ParseMode.HTML)

    file_path = await _download_track(track_id, track)
    if file_path and os.path.exists(file_path):
        try:
            from deezer_stream import is_deezer_ready
            is_full = is_deezer_ready() and os.path.getsize(file_path) > 500000
            label = "Полный трек" if is_full else "Превью 30 сек"
            await cb.message.answer_audio(
                FSInputFile(file_path),
                title=title,
                performer=artist,
                caption=f"🎵 {title} — {artist}\n\n▶️ {label}",
            )
            await status_msg.delete()
        except Exception as e:
            logger.error(f"Send audio error: {e}")
            await status_msg.edit_text("❌ Ошибка отправки аудио.")
        finally:
            try:
                os.remove(file_path)
            except Exception:
                pass
    else:
        await status_msg.edit_text("❌ Трек недоступен.")


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

    await cb.answer(t(cb.from_user.id, "processing", lang))
    status_msg = await cb.message.answer(f"📥 Скачиваю: <b>{title}</b> — {artist}...", parse_mode=ParseMode.HTML)

    file_path = await _download_track(track_id, track)
    if file_path and os.path.exists(file_path):
        try:
            from deezer_stream import is_deezer_ready
            is_full = is_deezer_ready() and os.path.getsize(file_path) > 500000
            label = "Полный трек" if is_full else "Превью 30 сек"
            await cb.message.answer_audio(
                FSInputFile(file_path),
                title=title,
                performer=artist,
                caption=f"📥 {title} — {artist}\n\n{label}",
            )
            await status_msg.delete()
        except Exception as e:
            logger.error(f"Send download error: {e}")
            await status_msg.edit_text("❌ Ошибка отправки.")
        finally:
            try:
                os.remove(file_path)
            except Exception:
                pass
    else:
        await status_msg.edit_text("❌ Трек недоступен.")


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
    is_photo = cb.message.photo or (cb.message.caption and not cb.message.text)

    cache = search_cache.get(cb.from_user.id)
    if cache and cache.get("results"):
        from keyboards import search_results_kb
        text = f"🔍 <b>Результаты поиска:</b>\n\nЗапрос: <i>{cache['query']}</i>"
        if is_photo:
            await cb.message.delete()
            await cb.message.answer(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=search_results_kb(cache["results"], cache["type"], page=0),
            )
        else:
            await cb.message.edit_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=search_results_kb(cache["results"], cache["type"], page=0),
            )
    else:
        from keyboards import main_menu_kb
        lang = (await get_user(cb.from_user.id) or {}).get("language", "ru")
        if is_photo:
            await cb.message.delete()
            await cb.message.answer(
                t(cb.from_user.id, "main_menu", lang),
                parse_mode=ParseMode.HTML,
                reply_markup=main_menu_kb(),
            )
        else:
            await cb.message.edit_text(
                t(cb.from_user.id, "main_menu", lang),
                parse_mode=ParseMode.HTML,
                reply_markup=main_menu_kb(),
            )
    await cb.answer()
