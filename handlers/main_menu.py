from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext

from database import register_user, get_user, get_user_stats
from keyboards import main_menu_kb, BACK_KB
from translations import t

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    await register_user(user.id, user.username, user.first_name)
    lang = (await get_user(user.id) or {}).get("language", "ru")
    await message.answer(
        t(user.id, "welcome", lang),
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_kb(),
    )


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    lang = (await get_user(cb.from_user.id) or {}).get("language", "ru")
    await cb.message.edit_text(
        t(cb.from_user.id, "main_menu", lang),
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_kb(),
    )
    await cb.answer()


@router.callback_query(F.data == "user_stats")
async def cb_user_stats(cb: CallbackQuery):
    stats = await get_user_stats(cb.from_user.id)
    lang = (await get_user(cb.from_user.id) or {}).get("language", "ru")
    text = (
        f"📊 <b>{t(cb.from_user.id, 'stats_title', lang)}</b>\n\n"
        f"{t(cb.from_user.id, 'stats_favorites', lang, count=stats['favorites'])}\n"
        f"{t(cb.from_user.id, 'stats_playlists', lang, count=stats['playlists'])}\n"
        f"{t(cb.from_user.id, 'stats_listens', lang, count=stats['listens'])}\n"
        f"{t(cb.from_user.id, 'stats_searches', lang, count=stats['searches'])}"
    )
    await cb.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=BACK_KB)
    await cb.answer()


@router.callback_query(F.data == "noop")
async def cb_noop(cb: CallbackQuery):
    await cb.answer()


@router.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "🎶 <b>Музыкальный бот</b>\n\n"
        "🔍 Поиск музыки по названию, исполнителю, альбому\n"
        "▶️ Прослушивание превью\n"
        "📥 Скачивание MP3\n"
        "❤️ Избранное\n"
        "📋 Плейлисты\n"
        "📝 Тексты песен\n"
        "🎲 Случайный трек\n"
        "📜 История поисков и прослушиваний\n\n"
        "Команды:\n"
        "/start — главное меню\n"
        "/help — эта справка\n"
        "/search — быстрый поиск\n"
    )
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=main_menu_kb())


@router.message(Command("search"))
async def cmd_search(message: Message, state: FSMContext):
    from handlers.search import SearchStates
    lang = (await get_user(message.from_user.id) or {}).get("language", "ru")
    await message.answer(
        t(message.from_user.id, "search_prompt", lang),
        reply_markup=BACK_KB,
    )
    await state.set_state(SearchStates.waiting_query)
