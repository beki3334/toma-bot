from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from database import (
    register_user, get_user, add_search_history, get_search_history,
)
from keyboards import (
    search_menu_kb, search_results_kb, BACK_KB,
)
from deezer import (
    search_tracks, search_artists, search_albums,
    format_track_info, get_chart,
)
from translations import t

router = Router()


class SearchStates(StatesGroup):
    waiting_query = State()
    waiting_genre = State()
    waiting_lyrics_query = State()


search_cache = {}


@router.callback_query(F.data == "search_menu")
async def cb_search_menu(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    lang = (await get_user(cb.from_user.id) or {}).get("language", "ru")
    await cb.message.edit_text(
        t(cb.from_user.id, "search_menu", lang),
        parse_mode=ParseMode.HTML,
        reply_markup=search_menu_kb(),
    )
    await cb.answer()


@router.callback_query(F.data == "search_type_track")
async def cb_search_track(cb: CallbackQuery, state: FSMContext):
    lang = (await get_user(cb.from_user.id) or {}).get("language", "ru")
    await cb.message.edit_text(
        t(cb.from_user.id, "search_prompt", lang),
        parse_mode=ParseMode.HTML,
        reply_markup=BACK_KB,
    )
    await state.set_state(SearchStates.waiting_query)
    await state.update_data(search_type="track")
    await cb.answer()


@router.callback_query(F.data == "search_type_artist")
async def cb_search_artist(cb: CallbackQuery, state: FSMContext):
    lang = (await get_user(cb.from_user.id) or {}).get("language", "ru")
    await cb.message.edit_text(
        t(cb.from_user.id, "enter_query", lang),
        parse_mode=ParseMode.HTML,
        reply_markup=BACK_KB,
    )
    await state.set_state(SearchStates.waiting_query)
    await state.update_data(search_type="artist")
    await cb.answer()


@router.callback_query(F.data == "search_type_album")
async def cb_search_album(cb: CallbackQuery, state: FSMContext):
    lang = (await get_user(cb.from_user.id) or {}).get("language", "ru")
    await cb.message.edit_text(
        t(cb.from_user.id, "enter_query", lang),
        parse_mode=ParseMode.HTML,
        reply_markup=BACK_KB,
    )
    await state.set_state(SearchStates.waiting_query)
    await state.update_data(search_type="album")
    await cb.answer()


@router.callback_query(F.data == "search_type_genre")
async def cb_search_genre(cb: CallbackQuery, state: FSMContext):
    lang = (await get_user(cb.from_user.id) or {}).get("language", "ru")
    await cb.message.edit_text(
        t(cb.from_user.id, "genre_prompt", lang),
        parse_mode=ParseMode.HTML,
        reply_markup=BACK_KB,
    )
    await state.set_state(SearchStates.waiting_genre)
    await cb.answer()


@router.callback_query(F.data == "search_type_lyrics")
async def cb_search_lyrics(cb: CallbackQuery, state: FSMContext):
    lang = (await get_user(cb.from_user.id) or {}).get("language", "ru")
    await cb.message.edit_text(
        t(cb.from_user.id, "enter_query", lang),
        parse_mode=ParseMode.HTML,
        reply_markup=BACK_KB,
    )
    await state.set_state(SearchStates.waiting_lyrics_query)
    await cb.answer()


@router.message(SearchStates.waiting_query)
async def handle_search_query(message: Message, state: FSMContext):
    data = await state.get_data()
    search_type = data.get("search_type", "track")
    query = message.text.strip()
    if not query or len(query) < 2:
        await message.answer("Минимум 2 символа.")
        return

    user_id = message.from_user.id
    if search_type == "track":
        results = await search_tracks(query)
    elif search_type == "artist":
        results = await search_artists(query)
    elif search_type == "album":
        results = await search_albums(query)
    else:
        results = await search_tracks(query)

    search_cache[user_id] = {"results": results, "type": search_type, "query": query}
    await add_search_history(user_id, query, search_type, len(results))

    lang = (await get_user(user_id) or {}).get("language", "ru")
    if not results:
        await message.answer(
            t(user_id, "no_results", lang, query=query),
            parse_mode=ParseMode.HTML,
            reply_markup=search_menu_kb(),
        )
        await state.clear()
        return

    text = f"🔍 <b>{t(user_id, 'search_results', lang)}</b>\n\n"
    text += f"Запрос: <i>{query}</i> — найдено: {len(results)}"
    await message.answer(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=search_results_kb(results, search_type, page=0),
    )
    await state.clear()


@router.message(SearchStates.waiting_genre)
async def handle_genre_query(message: Message, state: FSMContext):
    query = message.text.strip()
    if not query:
        return
    results = await search_tracks(query)
    user_id = message.from_user.id
    search_cache[user_id] = {"results": results, "type": "track", "query": query}
    await add_search_history(user_id, f"genre:{query}", "genre", len(results))

    lang = (await get_user(user_id) or {}).get("language", "ru")
    if not results:
        await message.answer(
            t(user_id, "no_results", lang, query=query),
            parse_mode=ParseMode.HTML,
            reply_markup=search_menu_kb(),
        )
        await state.clear()
        return

    text = f"🎸 <b>Жанр: {query}</b>\n\nНайдено: {len(results)}"
    await message.answer(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=search_results_kb(results, "track", page=0),
    )
    await state.clear()


@router.message(SearchStates.waiting_lyrics_query)
async def handle_lyrics_search(message: Message, state: FSMContext):
    query = message.text.strip()
    if not query:
        return
    results = await search_tracks(query)
    user_id = message.from_user.id
    search_cache[user_id] = {"results": results, "type": "track", "query": query}
    await add_search_history(user_id, f"lyrics:{query}", "lyrics", len(results))

    lang = (await get_user(user_id) or {}).get("language", "ru")
    if not results:
        await message.answer(
            t(user_id, "no_results", lang, query=query),
            parse_mode=ParseMode.HTML,
            reply_markup=search_menu_kb(),
        )
        await state.clear()
        return

    text = f"📝 <b>Поиск по тексту: {query}</b>\n\n"
    text += "Выберите трек и нажмите 📝 Текст песни\n\n"
    text += f"Найдено: {len(results)}"
    await message.answer(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=search_results_kb(results, "track", page=0),
    )
    await state.clear()


@router.callback_query(F.data.startswith("search_page_"))
async def cb_search_page(cb: CallbackQuery):
    parts = cb.data.split("_")
    search_type = parts[2]
    page = int(parts[3])
    user_id = cb.from_user.id
    cache = search_cache.get(user_id)
    if not cache or cache["type"] != search_type:
        await cb.answer("Кэш истёк. Сделайте новый поиск.", show_alert=True)
        return
    results = cache["results"]
    lang = (await get_user(user_id) or {}).get("language", "ru")
    text = f"🔍 <b>{t(user_id, 'search_results', lang)}</b>\n\n"
    text += f"Запрос: <i>{cache['query']}</i> — найдено: {len(results)}"
    await cb.message.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=search_results_kb(results, search_type, page),
    )
    await cb.answer()
