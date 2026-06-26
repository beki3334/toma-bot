import re
import logging
from datetime import datetime, date, timedelta
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import BOT_TOKEN, PROXY_URL, TIMEZONE
from database import (
    init_db, register_user, get_user, update_user_city,
    set_prayer_notifications, set_daily_summary,
    add_task, get_pending_tasks, get_today_tasks, get_tasks_by_category,
    get_all_pending_tasks, mark_done, delete_task, delete_all_done,
    get_users_with_prayer, get_users_with_daily, get_stats,
)
from prayer import get_prayer_times, get_prayer_message, find_city, CITIES
from keyboards import (
    main_menu_kb, categories_kb, repeat_kb, confirm_kb,
    tasks_list_kb, cities_kb, settings_kb, task_detail_kb,
    CATEGORIES, REPEAT_TYPES, BACK_KB,
)
from parser import parse_task

logging.basicConfig(level=logging.INFO)
dp = Dispatcher()
router = Router()
scheduler = AsyncIOScheduler(timezone=TIMEZONE)

bot: Bot = None


class TaskStates(StatesGroup):
    waiting_text = State()
    waiting_city = State()


async def send_reminder(user_id: int, text: str, task_id: int = None):
    try:
        kb = confirm_kb(task_id) if task_id else None
        await bot.send_message(
            user_id,
            f"🔔 *Напоминание:*\n{text}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb,
        )
    except Exception as e:
        logging.error(f"Reminder fail {user_id}: {e}")


async def send_prayer_notification(user: dict, prayer_name_ru: str):
    try:
        await bot.send_message(
            user["user_id"],
            f"🕌 Время намаза *{prayer_name_ru}* ({user.get('city', 'Москва')})",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        logging.error(f"Prayer notify fail {user['user_id']}: {e}")


async def send_daily_summary(user: dict):
    try:
        tasks = await get_today_tasks(user["user_id"])
        if not tasks:
            return
        lines = [f"☀️ *Доброе утро! План на сегодня ({user.get('city', '')}):*\n"]
        for t in tasks:
            remind = datetime.fromisoformat(t["remind_at"])
            cat = CATEGORIES.get(t["category"], "📌")
            lines.append(f"  {cat} `{remind.strftime('%H:%M')}` — {t['text']}")
        lines.append(f"\nВсего задач: {len(tasks)}")
        await bot.send_message(
            user["user_id"],
            "\n".join(lines),
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        logging.error(f"Daily summary fail {user['user_id']}: {e}")


async def schedule_prayer_for_user(user: dict):
    try:
        times = await get_prayer_times(user["latitude"], user["longitude"])
        today = date.today().isoformat()
        for ru_name, time_str in times.items():
            if ru_name == "Восход":
                continue
            h, m = map(int, time_str.split(":"))
            job_id = f"prayer_{user['user_id']}_{ru_name}_{today}"
            if scheduler.get_job(job_id):
                continue
            scheduler.add_job(
                send_prayer_notification,
                "cron", hour=h, minute=m,
                args=[user, ru_name],
                id=job_id, replace_existing=True,
            )
    except Exception as e:
        logging.error(f"Prayer schedule fail {user['user_id']}: {e}")


async def schedule_all_prayers():
    users = await get_users_with_prayer()
    for user in users:
        await schedule_prayer_for_user(user)


async def send_all_daily_summaries():
    users = await get_users_with_daily()
    for user in users:
        await send_daily_summary(user)


async def load_pending_tasks():
    tasks = await get_all_pending_tasks()
    for task in tasks:
        remind_at = datetime.fromisoformat(task["remind_at"])
        if remind_at > datetime.now():
            scheduler.add_job(
                send_reminder, "date", run_date=remind_at,
                args=[task["user_id"], task["text"], task["id"]],
                id=f"task_{task['id']}", replace_existing=True,
            )


async def create_task_from_message(message: Message, text: str, category: str = "other"):
    result = parse_task(text)
    if not result:
        await message.answer(
            "🤔 Напиши задачу с датой и временем:\n"
            "  `29.06.2026 в 12:00 про зарплату`\n"
            "  `завтра в 15:00 позвонить маме`\n"
            "  `в 14:00 читать книгу`\n"
            "  `через 30 минут кофе`\n\n"
            "Или нажми кнопку 👇",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_kb(),
        )
        return

    remind_at, task_text = result
    task_id = await add_task(message.from_user.id, task_text, remind_at.isoformat(), category)
    scheduler.add_job(
        send_reminder, "date", run_date=remind_at,
        args=[message.from_user.id, task_text, task_id],
        id=f"task_{task_id}", replace_existing=True,
    )
    cat_label = CATEGORIES.get(category, "📌")
    await message.answer(
        f"✅ *Задача создана!*\n"
        f"{cat_label} {task_text}\n"
        f"⏰ {remind_at.strftime('%d.%m.%Y в %H:%M')}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_kb(),
    )


# ─── /start ───
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await register_user(message.from_user.id)
    await state.clear()
    await message.answer(
        "👋 *Привет! Я TOMA — твой умный помощник.*\n\n"
        "📌 *Создание задач:* просто напиши\n"
        "  `29.06.2026 в 12:00 про зарплату`\n"
        "  `завтра в 15:00 позвонить маме`\n"
        "  `в 14:00 читать книгу`\n"
        "  `через 30 минут кофе`\n\n"
        "🕌 Намазы для любого города мира\n"
        "📋 Категории, повторы, статистика\n\n"
        "Нажми кнопку ниже 👇",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_kb(),
    )


# ─── Inline: Главное меню ───
@router.callback_query(F.data == "main_menu")
async def cb_main_menu(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text("📋 *Главное меню*", parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu_kb())
    await cb.answer()


# ─── Inline: Мои задачи ───
@router.callback_query(F.data == "my_tasks")
async def cb_my_tasks(cb: CallbackQuery):
    tasks = await get_pending_tasks(cb.from_user.id)
    if not tasks:
        await cb.message.edit_text("📭 Нет активных задач.", reply_markup=BACK_KB)
        await cb.answer()
        return
    lines = ["📋 *Ваши задачи:*\n"]
    for t in tasks[:20]:
        remind = datetime.fromisoformat(t["remind_at"])
        cat = CATEGORIES.get(t["category"], "📌")
        lines.append(f"{cat} `{t['id']}` — {t['text']}  ({remind.strftime('%d.%m %H:%M')})")
    await cb.message.edit_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=tasks_list_kb(tasks))
    await cb.answer()


# ─── Inline: Детали задачи ───
@router.callback_query(F.data.startswith("task_"))
async def cb_task_detail(cb: CallbackQuery):
    task_id = int(cb.data.split("_")[1])
    tasks = await get_pending_tasks(cb.from_user.id)
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        await cb.answer("Задача не найдена", show_alert=True)
        return
    remind = datetime.fromisoformat(task["remind_at"])
    cat = CATEGORIES.get(task["category"], "📌")
    rep = REPEAT_TYPES.get(task.get("repeat_type", "none"), "")
    text = (
        f"*{cat} Задача #{task['id']}*\n\n"
        f"📝 {task['text']}\n"
        f"⏰ {remind.strftime('%d.%m.%Y в %H:%M')}\n"
    )
    if rep and rep != "Без повтора":
        text += f"🔄 {rep}\n"
    await cb.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=task_detail_kb(task))
    await cb.answer()


# ─── Inline: Выполнено ───
@router.callback_query(F.data.startswith("done_"))
async def cb_done(cb: CallbackQuery):
    task_id = int(cb.data.split("_")[1])
    await mark_done(task_id)
    job_id = f"task_{task_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    await cb.answer("✅ Выполнено!", show_alert=True)
    tasks = await get_pending_tasks(cb.from_user.id)
    if tasks:
        lines = ["📋 *Ваши задачи:*\n"]
        for t in tasks[:20]:
            remind = datetime.fromisoformat(t["remind_at"])
            cat = CATEGORIES.get(t["category"], "📌")
            lines.append(f"{cat} `{t['id']}` — {t['text']}  ({remind.strftime('%d.%m %H:%M')})")
        await cb.message.edit_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=tasks_list_kb(tasks))
    else:
        await cb.message.edit_text("📭 Все задачи выполнены!", reply_markup=BACK_KB)


# ─── Inline: Удалить ───
@router.callback_query(F.data.startswith("del_"))
async def cb_delete(cb: CallbackQuery):
    task_id = int(cb.data.split("_")[1])
    deleted = await delete_task(task_id, cb.from_user.id)
    if deleted:
        job_id = f"task_{task_id}"
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
        await cb.answer("🗑 Удалено")
    else:
        await cb.answer("Не найдено", show_alert=True)
    await cb_my_tasks(cb)


# ─── Inline: Новая задача — выбор категории ───
@router.callback_query(F.data == "new_task")
async def cb_new_task(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_text("📂 *Выбери категорию:*", parse_mode=ParseMode.MARKDOWN, reply_markup=categories_kb())
    await cb.answer()


# ─── Inline: Категория выбрана ───
@router.callback_query(F.data.startswith("cat_"))
async def cb_category(cb: CallbackQuery, state: FSMContext):
    category = cb.data.split("_")[1]
    await state.update_data(category=category)
    await cb.message.edit_text(
        f"📝 *Категория: {CATEGORIES.get(category, '📌')}*\n\n"
        "Напиши задачу в формате:\n"
        "`в 14:00 сделать домашку`\n\n"
        "Или просто текст — я спрошу время отдельно.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=BACK_KB,
    )
    await state.set_state(TaskStates.waiting_text)
    await cb.answer()


# ─── Текст: обработка создания задачи ───
@router.message(TaskStates.waiting_text)
async def handle_task_text(message: Message, state: FSMContext):
    data = await state.get_data()
    category = data.get("category", "other")
    text = message.text.strip()

    result = parse_task(text)
    if result:
        remind_at, task_text = result
        task_id = await add_task(message.from_user.id, task_text, remind_at.isoformat(), category)
        scheduler.add_job(
            send_reminder, "date", run_date=remind_at,
            args=[message.from_user.id, task_text, task_id],
            id=f"task_{task_id}", replace_existing=True,
        )
        cat_label = CATEGORIES.get(category, "📌")
        await message.answer(
            f"✅ *Задача создана!*\n"
            f"{cat_label} {task_text}\n"
            f"⏰ {remind_at.strftime('%d.%m.%Y в %H:%M')}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_kb(),
        )
        await state.clear()
    else:
        await state.update_data(task_text=text)
        await message.answer(
            f"📝 Задача: *{text}*\n\n"
            "⏰ Когда напомнить?\n"
            "Напиши дату и время:\n"
            "  `29.06.2026 в 12:00`\n"
            "  `завтра в 15:00`\n"
            "  `в 14:00`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=BACK_KB,
        )
        await state.set_state(TaskStates.waiting_city)


# ─── Текст: время для задачи без времени ───
@router.message(TaskStates.waiting_city)
async def handle_time_input(message: Message, state: FSMContext):
    data = await state.get_data()

    # Если это ввод города
    if data.get("awaiting_city"):
        city_name = message.text.strip()
        city = find_city(city_name)
        if not city:
            await message.answer(
                f"❌ Город *{city_name}* не найден.\n"
                "Попробуй: Москва, Казань, Уфа, Ташкент, Стамбул, Дубай...",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        await update_user_city(message.from_user.id, city_name, city["lat"], city["lon"], city["tz"])
        user = await get_user(message.from_user.id)
        if user and user.get("prayer_notifications"):
            await schedule_prayer_for_user(user)
        await message.answer(
            f"✅ Город: *{city_name}*\n"
            f"🕌 Намазы будут для этого города.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_kb(),
        )
        await state.clear()
        return

    # Это ввод времени для задачи
    task_text = data.get("task_text", "")
    category = data.get("category", "other")
    result = parse_task(f"{message.text} {task_text}")
    if not result:
        await message.answer(
            "❌ Не могу распознать дату.\n"
            "Попробуй: `29.06.2026 в 12:00` или `завтра в 15:00`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    remind_at, _ = result
    task_id = await add_task(message.from_user.id, task_text, remind_at.isoformat(), category)
    scheduler.add_job(
        send_reminder, "date", run_date=remind_at,
        args=[message.from_user.id, task_text, task_id],
        id=f"task_{task_id}", replace_existing=True,
    )
    cat_label = CATEGORIES.get(category, "📌")
    await message.answer(
        f"✅ *Задача создана!*\n"
        f"{cat_label} {task_text}\n"
        f"⏰ {remind_at.strftime('%d.%m.%Y в %H:%M')}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_kb(),
    )
    await state.clear()


# ─── Inline: Время намазов ───
@router.callback_query(F.data == "prayer_times")
async def cb_prayer_times(cb: CallbackQuery):
    user = await get_user(cb.from_user.id)
    if not user:
        await register_user(cb.from_user.id)
        user = await get_user(cb.from_user.id)
    msg = await get_prayer_message(user["latitude"], user["longitude"], user["city"])
    await cb.message.edit_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=BACK_KB)
    await cb.answer()


# ─── Inline: Выбор города ───
@router.callback_query(F.data == "set_city")
async def cb_set_city(cb: CallbackQuery):
    await cb.message.edit_text("🏙 *Выбери город:*", parse_mode=ParseMode.MARKDOWN, reply_markup=cities_kb())
    await cb.answer()


# ─── Inline: Город из списка ───
@router.callback_query(F.data.startswith("city_"))
async def cb_city_selected(cb: CallbackQuery, state: FSMContext):
    city_name = cb.data.split("_", 1)[1]
    if city_name == "custom":
        await cb.message.edit_text(
            "✏ Напиши название города:",
            reply_markup=BACK_KB,
        )
        await state.update_data(awaiting_city=True)
        await state.set_state(TaskStates.waiting_city)
        await cb.answer()
        return
    city = find_city(city_name)
    if not city:
        await cb.answer("Город не найден", show_alert=True)
        return
    await update_user_city(cb.from_user.id, city_name, city["lat"], city["lon"], city["tz"])
    user = await get_user(cb.from_user.id)
    if user and user.get("prayer_notifications"):
        await schedule_prayer_for_user(user)
    await cb.message.edit_text(
        f"✅ Город: *{city_name}*\n🕌 Намазы будут для этого города.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_kb(),
    )
    await cb.answer()


# ─── Inline: Статистика ───
@router.callback_query(F.data == "stats")
async def cb_stats(cb: CallbackQuery):
    stats = await get_stats(cb.from_user.id)
    text = (
        f"📊 *Статистика*\n\n"
        f"⏳ Активных задач: *{stats['pending']}*\n"
        f"✅ Выполнено: *{stats['done']}*\n"
        f"📅 На сегодня: *{stats['today']}*"
    )
    await cb.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=BACK_KB)
    await cb.answer()


# ─── Inline: План на сегодня ───
@router.callback_query(F.data == "today_plan")
async def cb_today_plan(cb: CallbackQuery):
    tasks = await get_today_tasks(cb.from_user.id)
    user = await get_user(cb.from_user.id)
    city = user.get("city", "Москва") if user else "Москва"
    if not tasks:
        await cb.message.edit_text(
            f"📅 На сегодня задач нет.\n\n"
            f"🕌 Намазы: /prayer",
            reply_markup=BACK_KB,
        )
        await cb.answer()
        return
    lines = [f"📅 *План на сегодня ({city}):*\n"]
    for t in tasks:
        remind = datetime.fromisoformat(t["remind_at"])
        cat = CATEGORIES.get(t["category"], "📌")
        lines.append(f"{cat} `{remind.strftime('%H:%M')}` — {t['text']}")
    await cb.message.edit_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=BACK_KB)
    await cb.answer()


# ─── Inline: Очистить выполненные ───
@router.callback_query(F.data == "clear_done")
async def cb_clear_done(cb: CallbackQuery):
    count = await delete_all_done(cb.from_user.id)
    await cb.answer(f"🗑 Удалено: {count}", show_alert=True)


# ─── Inline: Настройки ───
@router.callback_query(F.data == "settings")
async def cb_settings(cb: CallbackQuery):
    user = await get_user(cb.from_user.id)
    if not user:
        await register_user(cb.from_user.id)
        user = await get_user(cb.from_user.id)
    await cb.message.edit_text("⚙ *Настройки:*", parse_mode=ParseMode.MARKDOWN, reply_markup=settings_kb(user))
    await cb.answer()


# ─── Inline: Переключить намазы ───
@router.callback_query(F.data == "toggle_prayer")
async def cb_toggle_prayer(cb: CallbackQuery):
    user = await get_user(cb.from_user.id)
    new_state = not user.get("prayer_notifications")
    await set_prayer_notifications(cb.from_user.id, new_state)
    if new_state:
        await schedule_prayer_for_user(user)
    user = await get_user(cb.from_user.id)
    status = "включены" if new_state else "выключены"
    await cb.answer(f"🕌 Уведомления о намазах {status}")
    await cb.message.edit_reply_markup(reply_markup=settings_kb(user))


# ─── Inline: Переключить сводку ───
@router.callback_query(F.data == "toggle_daily")
async def cb_toggle_daily(cb: CallbackQuery):
    user = await get_user(cb.from_user.id)
    new_state = not user.get("daily_summary")
    await set_daily_summary(cb.from_user.id, new_state)
    user = await get_user(cb.from_user.id)
    status = "включена" if new_state else "выключена"
    await cb.answer(f"📅 Утренняя сводка {status}")
    await cb.message.edit_reply_markup(reply_markup=settings_kb(user))


# ─── /tasks ───
@router.message(Command("tasks"))
async def cmd_tasks(message: Message):
    tasks = await get_pending_tasks(message.from_user.id)
    if not tasks:
        await message.answer("📭 Нет активных задач.", reply_markup=main_menu_kb())
        return
    lines = ["📋 *Ваши задачи:*\n"]
    for t in tasks[:20]:
        remind = datetime.fromisoformat(t["remind_at"])
        cat = CATEGORIES.get(t["category"], "📌")
        lines.append(f"{cat} `{t['id']}` — {t['text']}  ({remind.strftime('%d.%m %H:%M')})")
    await message.answer("\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=tasks_list_kb(tasks))


# ─── /prayer ───
@router.message(Command("prayer"))
async def cmd_prayer(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await register_user(message.from_user.id)
        user = await get_user(message.from_user.id)
    msg = await get_prayer_message(user["latitude"], user["longitude"], user["city"])
    await message.answer(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=BACK_KB)


# ─── /help ───
@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📋 *Команды:*\n"
        "/start — меню\n"
        "/tasks — задачи\n"
        "/prayer — намазы\n"
        "/help — помощь\n\n"
        "✏️ *Создание задач:*\n"
        "`29.06.2026 в 12:00 про зарплату`\n"
        "`завтра в 15:00 позвонить`\n"
        "`в 14:00 читать книгу`\n"
        "`через 30 минут кофе`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_kb(),
    )


# ─── Свободный текст (не в FSM) ───
@router.message(F.text)
async def handle_free_text(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        return
    await create_task_from_message(message, message.text.strip())


async def on_startup():
    global bot
    await init_db()
    await load_pending_tasks()
    await schedule_all_prayers()
    scheduler.add_job(schedule_all_prayers, CronTrigger(hour=0, minute=5), id="daily_prayers")
    scheduler.add_job(send_all_daily_summaries, CronTrigger(hour=7, minute=0), id="daily_summary")
    scheduler.start()
    logging.info("Bot started!")


async def main():
    global bot
    if PROXY_URL:
        from aiogram.client.session.aiohttp import AiohttpSession
        session = AiohttpSession(proxy=PROXY_URL)
        bot = Bot(token=BOT_TOKEN, session=session)
        logging.info(f"Using proxy: {PROXY_URL}")
    else:
        bot = Bot(token=BOT_TOKEN)
        logging.info("No proxy configured")

    dp.include_router(router)
    dp.startup.register(on_startup)
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
