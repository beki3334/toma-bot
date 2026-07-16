from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from database import (
    get_user, get_playlists, get_playlist, create_playlist, delete_playlist,
    rename_playlist, get_playlist_tracks, add_track_to_playlist,
    remove_track_from_playlist, get_playlist_track_count,
)
from deezer import get_track, format_duration, get_cover_url
from keyboards import (
    playlists_kb, playlist_detail_kb, playlist_tracks_kb,
    add_to_playlist_choice_kb, BACK_KB,
)
from translations import t

router = Router()


class PlaylistStates(StatesGroup):
    waiting_name = State()
    waiting_rename = State()


@router.callback_query(F.data == "playlists")
async def cb_playlists(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = cb.from_user.id
    playlists = await get_playlists(user_id)
    lang = (await get_user(user_id) or {}).get("language", "ru")

    if not playlists:
        await cb.message.edit_text(
            t(user_id, "playlists_empty", lang),
            parse_mode=ParseMode.HTML,
            reply_markup=playlists_kb([]),
        )
    else:
        text = f"📋 <b>{t(user_id, 'playlists_title', lang)}</b>\n\n"
        for p in playlists:
            text += f"📋 {p['name']} — {p.get('track_count', 0)} треков\n"
        await cb.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=playlists_kb(playlists))
    await cb.answer()


@router.callback_query(F.data.startswith("playlist_"))
async def cb_playlist_detail(cb: CallbackQuery):
    playlist_id = int(cb.data.split("_")[1])
    user_id = cb.from_user.id
    playlist = await get_playlist(playlist_id, user_id)
    if not playlist:
        await cb.answer("Плейлист не найден", show_alert=True)
        return

    lang = (await get_user(user_id) or {}).get("language", "ru")
    text = (
        f"📋 <b>{playlist['name']}</b>\n"
        f"🎵 Треков: {playlist.get('track_count', 0)}\n"
    )
    if playlist.get("description"):
        text += f"📝 {playlist['description']}\n"

    kb = playlist_detail_kb(playlist_id, is_owner=True)
    await cb.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.startswith("del_playlist_"))
async def cb_del_playlist(cb: CallbackQuery):
    playlist_id = int(cb.data.split("_")[2])
    user_id = cb.from_user.id
    playlist = await get_playlist(playlist_id, user_id)
    if not playlist:
        await cb.answer("Не найдено", show_alert=True)
        return

    lang = (await get_user(user_id) or {}).get("language", "ru")
    await cb.message.edit_text(
        t(user_id, "confirm_delete", lang, name=playlist["name"]),
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_del_pl_{playlist_id}"),
             InlineKeyboardButton(text="❌ Нет", callback_data=f"playlist_{playlist_id}")],
        ]),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("confirm_del_pl_"))
async def cb_confirm_del_pl(cb: CallbackQuery):
    playlist_id = int(cb.data.split("_")[3])
    deleted = await delete_playlist(playlist_id, cb.from_user.id)
    lang = (await get_user(cb.from_user.id) or {}).get("language", "ru")
    if deleted:
        await cb.answer(t(cb.from_user.id, "playlist_deleted", lang), show_alert=True)
        await cb.message.edit_text(
            t(cb.from_user.id, "playlists_empty", lang),
            parse_mode=ParseMode.HTML,
            reply_markup=BACK_KB,
        )
    else:
        await cb.answer("Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("rename_playlist_"))
async def cb_rename_playlist(cb: CallbackQuery, state: FSMContext):
    playlist_id = int(cb.data.split("_")[2])
    lang = (await get_user(cb.from_user.id) or {}).get("language", "ru")
    await cb.message.edit_text(t(cb.from_user.id, "rename_prompt", lang), reply_markup=BACK_KB)
    await state.set_state(PlaylistStates.waiting_rename)
    await state.update_data(playlist_id=playlist_id)
    await cb.answer()


@router.message(PlaylistStates.waiting_rename)
async def handle_rename(message: Message, state: FSMContext):
    data = await state.get_data()
    playlist_id = data.get("playlist_id")
    new_name = message.text.strip()
    if not new_name or len(new_name) > 50:
        await message.answer("Название: 1-50 символов.")
        return
    renamed = await rename_playlist(playlist_id, message.from_user.id, new_name)
    lang = (await get_user(message.from_user.id) or {}).get("language", "ru")
    if renamed:
        await message.answer(
            t(message.from_user.id, "playlist_renamed", lang),
            reply_markup=BACK_KB,
        )
    else:
        await message.answer("Ошибка.", reply_markup=BACK_KB)
    await state.clear()


@router.callback_query(F.data == "new_playlist")
async def cb_new_playlist(cb: CallbackQuery, state: FSMContext):
    lang = (await get_user(cb.from_user.id) or {}).get("language", "ru")
    await cb.message.edit_text(t(cb.from_user.id, "new_playlist_prompt", lang), reply_markup=BACK_KB)
    await state.set_state(PlaylistStates.waiting_name)
    await cb.answer()


@router.message(PlaylistStates.waiting_name)
async def handle_new_playlist(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name or len(name) > 50:
        await message.answer("Название: 1-50 символов.")
        return
    playlist_id = await create_playlist(message.from_user.id, name)
    lang = (await get_user(message.from_user.id) or {}).get("language", "ru")
    if playlist_id:
        await message.answer(
            t(message.from_user.id, "playlist_created", lang, name=name),
            reply_markup=BACK_KB,
        )
    else:
        await message.answer("Не удалось создать. Возможно, лимит плейлистов.", reply_markup=BACK_KB)
    await state.clear()


@router.callback_query(F.data.startswith("add_to_playlist_"))
async def cb_add_to_playlist(cb: CallbackQuery):
    track_id = int(cb.data.split("_")[2])
    user_id = cb.from_user.id
    playlists = await get_playlists(user_id)
    if not playlists:
        lang = (await get_user(user_id) or {}).get("language", "ru")
        await cb.message.edit_text(
            t(user_id, "playlists_empty", lang) + "\n\nСначала создайте плейлист.",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Создать плейлист", callback_data="new_playlist")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data=f"track_{track_id}")],
            ]),
        )
        await cb.answer()
        return
    kb = add_to_playlist_choice_kb(track_id, playlists)
    await cb.message.edit_text("📋 Выберите плейлист:", reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.startswith("save_to_pl_"))
async def cb_save_to_pl(cb: CallbackQuery):
    parts = cb.data.split("_")
    track_id = int(parts[2])
    playlist_id = int(parts[3])
    user_id = cb.from_user.id

    track_data = await get_track(track_id)
    if not track_data:
        await cb.answer("Трек не найден", show_alert=True)
        return

    added = await add_track_to_playlist(playlist_id, track_data, user_id)
    playlist = await get_playlist(playlist_id, user_id)
    lang = (await get_user(user_id) or {}).get("language", "ru")
    name = playlist["name"] if playlist else "?"

    if added:
        await cb.answer(t(user_id, "track_added_to_playlist", lang, name=name), show_alert=True)
    else:
        await cb.answer("Не удалось добавить (дубликат или лимит)", show_alert=True)

    in_fav = False
    try:
        from database import is_favorite
        in_fav = await is_favorite(user_id, track_id)
    except Exception:
        pass
    from keyboards import track_actions_kb
    await cb.message.edit_reply_markup(reply_markup=track_actions_kb(track_id, in_fav))


@router.callback_query(F.data.startswith("new_pl_for_"))
async def cb_new_pl_for_track(cb: CallbackQuery, state: FSMContext):
    track_id = int(cb.data.split("_")[3])
    lang = (await get_user(cb.from_user.id) or {}).get("language", "ru")
    await cb.message.edit_text(
        t(cb.from_user.id, "new_playlist_prompt", lang),
        reply_markup=BACK_KB,
    )
    await state.set_state(PlaylistStates.waiting_name)
    await state.update_data(for_track_id=track_id)
    await cb.answer()


@router.callback_query(F.data.startswith("play_playlist_"))
async def cb_play_playlist(cb: CallbackQuery):
    playlist_id = int(cb.data.split("_")[2])
    user_id = cb.from_user.id
    tracks = await get_playlist_tracks(playlist_id, user_id)
    if not tracks:
        lang = (await get_user(user_id) or {}).get("language", "ru")
        await cb.answer(t(user_id, "playlist_empty", lang), show_alert=True)
        return
    for t_data in tracks[:5]:
        preview = t_data.get("preview_url")
        if preview:
            import httpx
            import os
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.get(preview)
                    if resp.status_code == 200:
                        temp_path = f"temp_audio/pl_{t_data['track_id']}.mp3"
                        os.makedirs("temp_audio", exist_ok=True)
                        with open(temp_path, "wb") as f:
                            f.write(resp.content)
                        from aiogram.types import FSInputFile
                        await cb.message.answer_audio(
                            FSInputFile(temp_path),
                            title=t_data.get("track_title", "?"),
                            performer=t_data.get("artist_name", "?"),
                        )
                        try:
                            os.remove(temp_path)
                        except Exception:
                            pass
            except Exception:
                pass
    await cb.answer("Воспроизведение плейлиста")


@router.callback_query(F.data.startswith("pl_track_"))
async def cb_playlist_track(cb: CallbackQuery):
    parts = cb.data.split("_")
    playlist_id = int(parts[2])
    track_id = int(parts[3])
    from handlers.track import show_track_detail
    await cb.answer()
    await show_track_detail(cb, track_id, cb.from_user.id, edit=False)


@router.callback_query(F.data.startswith("pl_page_"))
async def cb_playlist_page(cb: CallbackQuery):
    parts = cb.data.split("_")
    playlist_id = int(parts[2])
    page = int(parts[3])
    user_id = cb.from_user.id
    tracks = await get_playlist_tracks(playlist_id, user_id)
    playlist = await get_playlist(playlist_id, user_id)
    if not tracks or not playlist:
        await cb.answer("Плейлист пуст", show_alert=True)
        return
    text = f"📋 <b>{playlist['name']}</b> ({len(tracks)} треков)\n\n"
    start = page * 5 + 1
    for i, t in enumerate(tracks[page * 5:(page + 1) * 5]):
        text += f"{start + i}. {t.get('track_title', '?')} — {t.get('artist_name', '?')}\n"
    kb = playlist_tracks_kb(playlist_id, tracks, page)
    await cb.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    await cb.answer()
