from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
)

CATEGORIES = {
    "study": "📚 Учёба",
    "work": "💼 Работа",
    "prayer": "🕌 Намаз",
    "health": "💪 Здоровье",
    "home": "🏠 Дом",
    "other": "📌 Другое",
}

REPEAT_TYPES = {
    "none": "Без повтора",
    "daily": "Каждый день",
    "weekly": "Каждую неделю",
    "monthly": "Каждый месяц",
}


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Мои задачи", callback_data="my_tasks"),
         InlineKeyboardButton(text="➕ Новая задача", callback_data="new_task")],
        [InlineKeyboardButton(text="🕌 Время намазов", callback_data="prayer_times"),
         InlineKeyboardButton(text="📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton(text="🏙 Выбрать город", callback_data="set_city"),
         InlineKeyboardButton(text="📅 План на сегодня", callback_data="today_plan")],
        [InlineKeyboardButton(text="🗑 Очистить done", callback_data="clear_done")],
    ])


def categories_kb() -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for key, label in CATEGORIES.items():
        row.append(InlineKeyboardButton(text=label, callback_data=f"cat_{key}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def repeat_kb() -> InlineKeyboardMarkup:
    buttons = []
    for key, label in REPEAT_TYPES.items():
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"rep_{key}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_kb(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Готово", callback_data=f"done_{task_id}"),
         InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del_{task_id}")],
    ])


def tasks_list_kb(tasks: list) -> InlineKeyboardMarkup:
    buttons = []
    for t in tasks[:20]:
        text = f"{'✅' if t['done'] else '⏳'} {t['text'][:30]}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"task_{t['id']}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def cities_kb() -> InlineKeyboardMarkup:
    cities = [
        ("🇷🇺 Москва", "city_москва"), ("🇷У Казань", "city_казань"),
        ("🇷У Уфа", "city_уфа"), ("🇷У Махачкала", "city_махачкала"),
        ("🇷У Грозный", "city_грозный"), ("🇷У СПб", "city_спб"),
        ("🇺🇿 Ташкент", "city_ташкент"), ("🇹🇷 Стамбул", "city_стамбул"),
        ("🇦🇪 Дубай", "city_дубай"), ("🇸А Эр-Рияд", "city_эр-рияд"),
        ("🇪🇬 Каир", "city_каир"), ("🇬🇧 Лондон", "city_лондон"),
    ]
    buttons = []
    for i in range(0, len(cities), 2):
        row = [InlineKeyboardButton(text=cities[i][0], callback_data=cities[i][1])]
        if i + 1 < len(cities):
            row.append(InlineKeyboardButton(text=cities[i+1][0], callback_data=cities[i+1][1]))
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="✏ Свой город", callback_data="city_custom")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def task_detail_kb(task: dict) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="✅ Выполнено", callback_data=f"done_{task['id']}"),
         InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del_{task['id']}")],
    ]
    if task.get("repeat_type") and task["repeat_type"] != "none":
        buttons.append([InlineKeyboardButton(text="⏹ Остановить повтор", callback_data=f"stoprep_{task['id']}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="my_tasks")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


BACK_KB = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
])
