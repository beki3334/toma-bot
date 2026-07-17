from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
)
from deezer_api import format_duration

BACK_KB = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
])


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Поиск", callback_data="search_menu"),
         InlineKeyboardButton(text="🎲 Случайный", callback_data="random_track")],
        [InlineKeyboardButton(text="❤️ Избранное", callback_data="favorites"),
         InlineKeyboardButton(text="📋 Плейлисты", callback_data="playlists")],
        [InlineKeyboardButton(text="📜 История", callback_data="history_menu"),
         InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")],
    ])


def search_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎵 Трек", callback_data="search_type_track"),
         InlineKeyboardButton(text="👤 Исполнитель", callback_data="search_type_artist")],
        [InlineKeyboardButton(text="💿 Альбом", callback_data="search_type_album"),
         InlineKeyboardButton(text="🎸 Жанр", callback_data="search_type_genre")],
        [InlineKeyboardButton(text="📝 Текст песни", callback_data="search_type_lyrics")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")],
    ])


def track_actions_kb(track_id: int, in_favorites: bool = False, playlist_id: int = None) -> InlineKeyboardMarkup:
    fav_emoji = "💔" if in_favorites else "❤️"
    fav_data = f"unfav_{track_id}" if in_favorites else f"fav_{track_id}"
    buttons = [
        [InlineKeyboardButton(text="▶️ Слушать", callback_data=f"play_{track_id}"),
         InlineKeyboardButton(text="📥 Скачать", callback_data=f"download_{track_id}")],
        [InlineKeyboardButton(text=f"{fav_emoji} Избранное", callback_data=fav_data),
         InlineKeyboardButton(text="📝 Текст", callback_data=f"lyrics_{track_id}")],
        [InlineKeyboardButton(text="👤 Артист", callback_data=f"artist_from_track_{track_id}"),
         InlineKeyboardButton(text="💿 Альбом", callback_data=f"album_from_track_{track_id}")],
        [InlineKeyboardButton(text="➕ В плейлист", callback_data=f"add_to_playlist_{track_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_from_track")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def artist_kb(artist_id: int, artist_name: str = "") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎵 Топ", callback_data=f"artist_top_{artist_id}"),
         InlineKeyboardButton(text="💿 Альбомы", callback_data=f"artist_albums_{artist_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_from_artist")],
    ])


def album_kb(album_id: int, album_title: str = "") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎵 Треки", callback_data=f"album_tracks_{album_id}"),
         InlineKeyboardButton(text="👤 Артист", callback_data=f"artist_from_album_{album_id}")],
        [InlineKeyboardButton(text="➕ В плейлист", callback_data=f"add_album_to_playlist_{album_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_from_album")],
    ])


def favorites_kb(page: int = 0, total: int = 0, has_prev: bool = False, has_next: bool = False) -> InlineKeyboardMarkup:
    nav = []
    if has_prev:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"fav_page_{page - 1}"))
    if total > 0:
        nav.append(InlineKeyboardButton(text=f"{page + 1}/{total}", callback_data="noop"))
    if has_next:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"fav_page_{page + 1}"))
    buttons = []
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton(text="🗑 Очистить", callback_data="clear_favorites")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def playlists_kb(playlists: list) -> InlineKeyboardMarkup:
    buttons = []
    for p in playlists:
        count = p.get("track_count", 0)
        buttons.append([InlineKeyboardButton(
            text=f"📋 {p['name']} ({count})",
            callback_data=f"playlist_{p['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="➕ Новый", callback_data="new_playlist")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def playlist_detail_kb(playlist_id: int, is_owner: bool = True) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="▶️ Все", callback_data=f"play_playlist_{playlist_id}"),
         InlineKeyboardButton(text="✏️ Переименовать", callback_data=f"rename_playlist_{playlist_id}")],
    ]
    if is_owner:
        buttons.append([InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del_playlist_{playlist_id}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="playlists")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def playlist_tracks_kb(playlist_id: int, tracks: list, page: int = 0, per_page: int = 5) -> InlineKeyboardMarkup:
    start = page * per_page
    end = start + per_page
    page_tracks = tracks[start:end]
    buttons = []
    for i, t in enumerate(page_tracks):
        pos = start + i + 1
        buttons.append([InlineKeyboardButton(
            text=f"{pos}. {t.get('track_title', '?')[:25]}",
            callback_data=f"pl_track_{playlist_id}_{t['track_id']}"
        )])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"pl_page_{playlist_id}_{page - 1}"))
    total_pages = (len(tracks) + per_page - 1) // per_page
    if total_pages > 1:
        nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
    if end < len(tracks):
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"pl_page_{playlist_id}_{page + 1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"playlist_{playlist_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def history_kb(history_type: str = "listen") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎧 Слушали", callback_data="history_listen"),
         InlineKeyboardButton(text="🔍 Поиски", callback_data="history_search")],
        [InlineKeyboardButton(text="🗑 Очистить", callback_data=f"clear_history_{history_type}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")],
    ])


def settings_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Язык", callback_data="set_language"),
         InlineKeyboardButton(text="🔔 Уведомления", callback_data="toggle_notifications")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")],
    ])


def language_kb() -> InlineKeyboardMarkup:
    from config import SUPPORTED_LANGUAGES
    buttons = []
    for code, name in SUPPORTED_LANGUAGES.items():
        buttons.append([InlineKeyboardButton(text=name, callback_data=f"lang_{code}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="settings")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def search_results_kb(results: list, search_type: str = "track", page: int = 0, per_page: int = 5) -> InlineKeyboardMarkup:
    start = page * per_page
    end = start + per_page
    page_results = results[start:end]
    buttons = []
    for i, item in enumerate(page_results):
        pos = start + i + 1
        if search_type == "track":
            title = item.get("title", "?")[:22]
            artist = item.get("artist", {}).get("name", "?")[:15]
            text = f"{pos}. {title} — {artist}"
            data = f"track_{item['id']}"
        elif search_type == "artist":
            name = item.get("name", "?")[:30]
            text = f"{pos}. {name}"
            data = f"artist_{item['id']}"
        elif search_type == "album":
            title = item.get("title", "?")[:22]
            artist = item.get("artist", {}).get("name", "?")[:15]
            text = f"{pos}. {title} — {artist}"
            data = f"album_{item['id']}"
        else:
            text = f"{pos}. {str(item)[:30]}"
            data = f"track_{item.get('id', 0)}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=data)])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"search_page_{search_type}_{page - 1}"))
    total_pages = (len(results) + per_page - 1) // per_page
    if total_pages > 1:
        nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
    if end < len(results):
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"search_page_{search_type}_{page + 1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton(text="🔄 Новый поиск", callback_data="search_menu")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_kb(action: str, item_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_{action}_{item_id}"),
         InlineKeyboardButton(text="❌ Нет", callback_data="main_menu")],
    ])


def add_to_playlist_choice_kb(track_id: int, playlists: list) -> InlineKeyboardMarkup:
    buttons = []
    for p in playlists:
        buttons.append([InlineKeyboardButton(
            text=f"📋 {p['name'][:30]}",
            callback_data=f"save_to_pl_{track_id}_{p['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="➕ Новый плейлист", callback_data=f"new_pl_for_{track_id}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"track_{track_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
