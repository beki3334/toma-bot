from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from database import (
    register_user, get_user, add_search_history, get_search_history,
)
from keyboards import (
    search_menu_kb, search_results_kb, BACK_KB,
)
from deezer_api import (
    search_tracks, search_artists, search_albums,
    get_artist_top_tracks, get_artist, format_track_info, get_chart,
    format_duration,
)
from translations import t

router = Router()


class SearchStates(StatesGroup):
    waiting_query = State()
    waiting_genre = State()
    waiting_lyrics_query = State()


search_cache = {}
RESULTS_PER_PAGE = 10


def _tracks_kb(results: list, page: int = 0) -> InlineKeyboardMarkup:
    start = page * RESULTS_PER_PAGE
    end = start + RESULTS_PER_PAGE
    page_items = results[start:end]
    buttons = []
    for i, item in enumerate(page_items):
        pos = start + i + 1
        title = item.get("title", "?")[:25]
        artist = item.get("artist", {}).get("name", "?")[:18]
        dur = format_duration(item.get("duration", 0))
        buttons.append([InlineKeyboardButton(
            text=f"{pos}. {title} — {artist} ({dur})",
            callback_data=f"track_{item['id']}"
        )])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"spage_{page - 1}"))
    total_pages = (len(results) + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE
    if total_pages > 1:
        nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
    if end < len(results):
        nav.append(InlineKeyboardButton(text="Ещё ➡️", callback_data=f"spage_{page + 1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton(text="🔄 Новый поиск", callback_data="search_menu")])
    buttons.append([InlineKeyboardButton(text="🔙 Меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


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
        "👤 Введи имя исполнителя:",
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
    results = []

    if search_type == "artist":
        artists = await search_artists(query, limit=3)
        if artists:
            artist = artists[0]
            artist_id = artist["id"]
            artist_name = artist.get("name", "?")
            top_tracks = await get_artist_top_tracks(artist_id, limit=50)
            if top_tracks:
                results = top_tracks
                text = f"👤 <b>{artist_name}</b>\n\nТоп треков: {len(results)}"
            else:
                text = f"👤 <b>{artist_name}</b> — треков не найдено"
        else:
            text = f"😔 Исполнитель «{query}» не найден"
    elif search_type == "track":
        results = await search_tracks(query, limit=50)
        text = f"🔍 Найдено треков: {len(results)}"
    elif search_type == "album":
        results = await search_albums(query, limit=50)
        text = f"🔍 Найдено альбомов: {len(results)}"
    else:
        results = await search_tracks(query, limit=50)
        text = f"🔍 Найдено: {len(results)}"

    search_cache[user_id] = {"results": results, "type": "track", "query": query, "page": 0}
    await add_search_history(user_id, query, search_type, len(results))

    if not results:
        await message.answer(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=search_menu_kb(),
        )
        await state.clear()
        return

    await message.answer(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=_tracks_kb(results, page=0),
    )
    await state.clear()


@router.message(SearchStates.waiting_genre)
async def handle_genre_query(message: Message, state: FSMContext):
    query = message.text.strip()
    if not query:
        return
    results = await search_tracks(query, limit=50)
    user_id = message.from_user.id
    search_cache[user_id] = {"results": results, "type": "track", "query": query, "page": 0}
    await add_search_history(user_id, f"genre:{query}", "genre", len(results))

    if not results:
        await message.answer(
            f"🎸 Жанр «{query}» — ничего не найдено",
            parse_mode=ParseMode.HTML,
            reply_markup=search_menu_kb(),
        )
        await state.clear()
        return

    text = f"🎸 <b>Жанр: {query}</b>\n\nНайдено: {len(results)}"
    await message.answer(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=_tracks_kb(results, page=0),
    )
    await state.clear()


@router.message(SearchStates.waiting_lyrics_query)
async def handle_lyrics_search(message: Message, state: FSMContext):
    query = message.text.strip()
    if not query:
        return
    results = await search_tracks(query, limit=50)
    user_id = message.from_user.id
    search_cache[user_id] = {"results": results, "type": "track", "query": query, "page": 0}
    await add_search_history(user_id, f"lyrics:{query}", "lyrics", len(results))

    if not results:
        await message.answer(
            f"📝 По тексту «{query}» — ничего не найдено",
            parse_mode=ParseMode.HTML,
            reply_markup=search_menu_kb(),
        )
        await state.clear()
        return

    text = f"📝 <b>По тексту: {query}</b>\n\nВыбери трек → нажми 📝 Текст\n\nНайдено: {len(results)}"
    await message.answer(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=_tracks_kb(results, page=0),
    )
    await state.clear()


@router.callback_query(F.data.startswith("spage_"))
async def cb_search_page(cb: CallbackQuery):
    page = int(cb.data.split("_")[1])
    user_id = cb.from_user.id
    cache = search_cache.get(user_id)
    if not cache:
        await cb.answer("Кэш истёк. Сделайте новый поиск.", show_alert=True)
        return
    results = cache["results"]
    total = len(results)
    start = page * RESULTS_PER_PAGE + 1
    end = min((page + 1) * RESULTS_PER_PAGE, total)
    await cb.message.edit_text(
        f"🔍 Результаты: {start}-{end} из {total}",
        parse_mode=ParseMode.HTML,
        reply_markup=_tracks_kb(results, page),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("search_page_"))
async def cb_search_page_old(cb: CallbackQuery):
    parts = cb.data.split("_")
    search_type = parts[2]
    page = int(parts[3])
    user_id = cb.from_user.id
    cache = search_cache.get(user_id)
    if not cache:
        await cb.answer("Кэш истёк.", show_alert=True)
        return
    results = cache["results"]
    total = len(results)
    start = page * RESULTS_PER_PAGE + 1
    end = min((page + 1) * RESULTS_PER_PAGE, total)
    await cb.message.edit_text(
        f"🔍 Результаты: {start}-{end} из {total}",
        parse_mode=ParseMode.HTML,
        reply_markup=_tracks_kb(results, page),
    )
    await cb.answer()
