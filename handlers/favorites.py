from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

from database import get_user, get_favorites, get_favorites_count, clear_search_history
from keyboards import favorites_kb, track_actions_kb, BACK_KB
from translations import t

router = Router()

FAV_PER_PAGE = 5


@router.callback_query(F.data == "favorites")
async def cb_favorites(cb: CallbackQuery):
    user_id = cb.from_user.id
    total = await get_favorites_count(user_id)
    if total == 0:
        lang = (await get_user(user_id) or {}).get("language", "ru")
        await cb.message.edit_text(
            t(user_id, "favorites_empty", lang),
            parse_mode=ParseMode.HTML,
            reply_markup=BACK_KB,
        )
        await cb.answer()
        return
    await _show_favorites_page(cb, 0)


async def _show_favorites_page(cb: CallbackQuery, page: int):
    user_id = cb.from_user.id
    lang = (await get_user(user_id) or {}).get("language", "ru")
    total = await get_favorites_count(user_id)
    total_pages = (total + FAV_PER_PAGE - 1) // FAV_PER_PAGE

    favs = await get_favorites(user_id, limit=FAV_PER_PAGE, offset=page * FAV_PER_PAGE)

    text = f"❤️ <b>{t(user_id, 'favorites_title', lang, count=total)}</b>\n\n"
    start = page * FAV_PER_PAGE + 1
    for i, f in enumerate(favs):
        num = start + i
        text += f"{num}. 🎵 {f['track_title']} — {f['artist_name']}\n"

    kb = favorites_kb(page, total_pages, page > 0, page < total_pages - 1)
    await cb.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.startswith("fav_page_"))
async def cb_fav_page(cb: CallbackQuery):
    page = int(cb.data.split("_")[2])
    await _show_favorites_page(cb, page)


@router.callback_query(F.data == "clear_favorites")
async def cb_clear_favorites(cb: CallbackQuery):
    lang = (await get_user(cb.from_user.id) or {}).get("language", "ru")
    await cb.message.edit_text(
        t(cb.from_user.id, "confirm_clear_favorites", lang),
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да", callback_data="confirm_clear_fav"),
             InlineKeyboardButton(text="❌ Нет", callback_data="favorites")],
        ]),
    )
    await cb.answer()


@router.callback_query(F.data == "confirm_clear_fav")
async def cb_confirm_clear_fav(cb: CallbackQuery):
    from database import DB_PATH
    import aiosqlite
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM favorites WHERE user_id=?", (cb.from_user.id,))
        await db.commit()
    lang = (await get_user(cb.from_user.id) or {}).get("language", "ru")
    await cb.message.edit_text(
        t(cb.from_user.id, "favorites_empty", lang),
        parse_mode=ParseMode.HTML,
        reply_markup=BACK_KB,
    )
    await cb.answer("Избранное очищено", show_alert=True)
