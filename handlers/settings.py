from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.enums import ParseMode

from database import get_user, set_language, get_user_settings, update_user_setting
from keyboards import settings_kb, language_kb, BACK_KB
from translations import t, T

router = Router()


@router.callback_query(F.data == "settings")
async def cb_settings(cb: CallbackQuery):
    user_id = cb.from_user.id
    lang = (await get_user(user_id) or {}).get("language", "ru")
    settings = await get_user_settings(user_id)

    notif = "🔔 ВКЛ" if settings.get("notifications") else "🔕 ВЫКЛ"

    text = (
        f"⚙️ <b>{t(user_id, 'settings', lang)}</b>\n\n"
        f"🌐 Язык: {T.get(lang, {}).get('ru', lang)}\n"
        f"🔔 Уведомления: {notif}"
    )
    await cb.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=settings_kb())
    await cb.answer()


@router.callback_query(F.data == "set_language")
async def cb_set_language(cb: CallbackQuery):
    await cb.message.edit_text("🌐 Выберите язык:", reply_markup=language_kb())
    await cb.answer()


@router.callback_query(F.data.startswith("lang_"))
async def cb_language_selected(cb: CallbackQuery):
    lang = cb.data.split("_")[1]
    user_id = cb.from_user.id
    await set_language(user_id, lang)
    await cb.answer(t(user_id, "language_set", lang, lang=T.get(lang, {}).get("ru", lang)), show_alert=True)

    from keyboards import main_menu_kb
    await cb.message.edit_text(
        t(user_id, "main_menu", lang),
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_kb(),
    )


@router.callback_query(F.data == "toggle_notifications")
async def cb_toggle_notifications(cb: CallbackQuery):
    user_id = cb.from_user.id
    settings = await get_user_settings(user_id)
    new_val = 0 if settings.get("notifications") else 1
    await update_user_setting(user_id, "notifications", new_val)
    lang = (await get_user(user_id) or {}).get("language", "ru")
    key = "notifications_on" if new_val else "notifications_off"
    await cb.answer(t(user_id, key, lang), show_alert=True)

    await cb_settings(cb)
