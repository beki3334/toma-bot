from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

from database import (
    get_user, get_listen_history, get_search_history,
    clear_listen_history, clear_search_history,
)
from keyboards import history_kb, BACK_KB
from translations import t

router = Router()


@router.callback_query(F.data == "history_menu")
async def cb_history_menu(cb: CallbackQuery):
    lang = (await get_user(cb.from_user.id) or {}).get("language", "ru")
    await cb.message.edit_text(
        "📜 <b>История</b>\n\nВыберите тип:",
        parse_mode=ParseMode.HTML,
        reply_markup=history_kb(),
    )
    await cb.answer()


@router.callback_query(F.data == "history_listen")
async def cb_history_listen(cb: CallbackQuery):
    user_id = cb.from_user.id
    lang = (await get_user(user_id) or {}).get("language", "ru")
    history = await get_listen_history(user_id, limit=15)

    if not history:
        await cb.message.edit_text(
            t(user_id, "history_empty", lang),
            parse_mode=ParseMode.HTML,
            reply_markup=history_kb("listen"),
        )
        await cb.answer()
        return

    text = f"🎧 <b>{t(user_id, 'history_listen', lang)}</b>\n\n"
    buttons = []
    for i, h in enumerate(history, 1):
        text += f"{i}. 🎵 {h['track_title']} — {h['artist_name']}\n"
        buttons.append([InlineKeyboardButton(
            text=f"🎵 {h['track_title'][:30]}",
            callback_data=f"track_{h['track_id']}"
        )])
    buttons.append([InlineKeyboardButton(text="🗑 Очистить историю", callback_data="clear_history_listen")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="history_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await cb.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data == "history_search")
async def cb_history_search(cb: CallbackQuery):
    user_id = cb.from_user.id
    lang = (await get_user(user_id) or {}).get("language", "ru")
    history = await get_search_history(user_id, limit=15)

    if not history:
        await cb.message.edit_text(
            t(user_id, "history_empty", lang),
            parse_mode=ParseMode.HTML,
            reply_markup=history_kb("search"),
        )
        await cb.answer()
        return

    text = f"🔍 <b>{t(user_id, 'history_search', lang)}</b>\n\n"
    buttons = []
    for h in history:
        q = h["query"][:30]
        st = h.get("search_type", "track")
        emoji = {"track": "🎵", "artist": "👤", "album": "💿", "genre": "🎸", "lyrics": "📝"}.get(st, "🔍")
        buttons.append([InlineKeyboardButton(
            text=f"{emoji} {q}",
            callback_data=f"repeat_search_{st}_{h['query'][:20]}"
        )])
    buttons.append([InlineKeyboardButton(text="🗑 Очистить историю", callback_data="clear_history_search")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="history_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await cb.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.startswith("repeat_search_"))
async def cb_repeat_search(cb: CallbackQuery):
    parts = cb.data.split("_", 3)
    search_type = parts[2]
    query = parts[3] if len(parts) > 3 else ""

    if search_type in ("track", "artist", "album"):
        from handlers.search import search_cache, SearchStates
        from deezer_api import search_tracks, search_artists, search_albums
        from keyboards import search_results_kb

        if search_type == "track":
            results = await search_tracks(query)
        elif search_type == "artist":
            results = await search_artists(query)
        else:
            results = await search_albums(query)

        user_id = cb.from_user.id
        search_cache[user_id] = {"results": results, "type": search_type, "query": query}

        lang = (await get_user(user_id) or {}).get("language", "ru")
        if not results:
            await cb.message.edit_text(
                t(user_id, "no_results", lang, query=query),
                parse_mode=ParseMode.HTML,
                reply_markup=BACK_KB,
            )
        else:
            text = f"🔍 Результаты: <i>{query}</i> — {len(results)}"
            await cb.message.edit_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=search_results_kb(results, search_type, page=0),
            )
    await cb.answer()


@router.callback_query(F.data.startswith("clear_history_"))
async def cb_clear_history(cb: CallbackQuery):
    history_type = cb.data.split("_")[2]
    user_id = cb.from_user.id
    lang = (await get_user(user_id) or {}).get("language", "ru")

    if history_type == "listen":
        await clear_listen_history(user_id)
    elif history_type == "search":
        await clear_search_history(user_id)

    await cb.answer(t(user_id, "history_cleared", lang), show_alert=True)
    await cb.message.edit_text(
        t(user_id, "history_empty", lang),
        parse_mode=ParseMode.HTML,
        reply_markup=history_kb(history_type),
    )
