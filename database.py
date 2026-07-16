import aiosqlite
from datetime import datetime
from config import DB_PATH, MAX_FAVORITES, MAX_PLAYLISTS, MAX_PLAYLIST_TRACKS, MAX_HISTORY


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                language TEXT DEFAULT 'ru',
                created_at TEXT,
                last_active TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                track_id INTEGER NOT NULL,
                track_title TEXT,
                artist_name TEXT,
                album_title TEXT,
                preview_url TEXT,
                cover_url TEXT,
                duration INTEGER,
                created_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                UNIQUE(user_id, track_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS playlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                cover_url TEXT,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS playlist_tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                playlist_id INTEGER NOT NULL,
                track_id INTEGER NOT NULL,
                track_title TEXT,
                artist_name TEXT,
                album_title TEXT,
                preview_url TEXT,
                cover_url TEXT,
                duration INTEGER,
                position INTEGER DEFAULT 0,
                added_at TEXT,
                FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
                UNIQUE(playlist_id, track_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                query TEXT NOT NULL,
                search_type TEXT DEFAULT 'track',
                results_count INTEGER DEFAULT 0,
                created_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS listen_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                track_id INTEGER NOT NULL,
                track_title TEXT,
                artist_name TEXT,
                album_title TEXT,
                preview_url TEXT,
                cover_url TEXT,
                duration INTEGER,
                created_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                notifications INTEGER DEFAULT 1,
                auto_play INTEGER DEFAULT 0,
                quality TEXT DEFAULT 'standard',
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        await db.commit()


# ─── Users ───

async def register_user(user_id: int, username: str = None, first_name: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR IGNORE INTO users (user_id, username, first_name, created_at, last_active)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, username, first_name, datetime.now().isoformat(), datetime.now().isoformat())
        )
        await db.execute(
            "UPDATE users SET last_active=?, username=COALESCE(?, username), first_name=COALESCE(?, first_name) WHERE user_id=?",
            (datetime.now().isoformat(), username, first_name, user_id)
        )
        await db.execute(
            "INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)", (user_id,)
        )
        await db.commit()


async def get_user(user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def set_language(user_id: int, language: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET language=? WHERE user_id=?", (language, user_id))
        await db.commit()


async def get_user_language(user_id: int) -> str:
    user = await get_user(user_id)
    return user["language"] if user else "ru"


# ─── Favorites ───

async def add_favorite(user_id: int, track: dict) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        count_cursor = await db.execute(
            "SELECT COUNT(*) FROM favorites WHERE user_id=?", (user_id,)
        )
        count = (await count_cursor.fetchone())[0]
        if count >= MAX_FAVORITES:
            return False
        try:
            await db.execute(
                """INSERT OR IGNORE INTO favorites
                   (user_id, track_id, track_title, artist_name, album_title, preview_url, cover_url, duration, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, track["id"], track.get("title", ""), track.get("artist", {}).get("name", ""),
                 track.get("album", {}).get("title", ""), track.get("preview", ""),
                 track.get("album", {}).get("cover_xl") or track.get("album", {}).get("cover_big") or track.get("album", {}).get("cover_medium", ""),
                 track.get("duration", 0), datetime.now().isoformat())
            )
            await db.commit()
            return True
        except Exception:
            return False


async def remove_favorite(user_id: int, track_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM favorites WHERE user_id=? AND track_id=?", (user_id, track_id)
        )
        await db.commit()
        return cursor.rowcount > 0


async def is_favorite(user_id: int, track_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT 1 FROM favorites WHERE user_id=? AND track_id=?", (user_id, track_id)
        )
        return await cursor.fetchone() is not None


async def get_favorites(user_id: int, limit: int = 50, offset: int = 0) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM favorites WHERE user_id=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (user_id, limit, offset)
        )
        return [dict(r) for r in await cursor.fetchall()]


async def get_favorites_count(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM favorites WHERE user_id=?", (user_id,)
        )
        return (await cursor.fetchone())[0]


# ─── Playlists ───

async def create_playlist(user_id: int, name: str, description: str = "") -> int | None:
    async with aiosqlite.connect(DB_PATH) as db:
        count_cursor = await db.execute(
            "SELECT COUNT(*) FROM playlists WHERE user_id=?", (user_id,)
        )
        count = (await count_cursor.fetchone())[0]
        if count >= MAX_PLAYLISTS:
            return None
        now = datetime.now().isoformat()
        cursor = await db.execute(
            "INSERT INTO playlists (user_id, name, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, name, description, now, now)
        )
        await db.commit()
        return cursor.lastrowid


async def delete_playlist(playlist_id: int, user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM playlists WHERE id=? AND user_id=?", (playlist_id, user_id)
        )
        await db.commit()
        return cursor.rowcount > 0


async def rename_playlist(playlist_id: int, user_id: int, new_name: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "UPDATE playlists SET name=?, updated_at=? WHERE id=? AND user_id=?",
            (new_name, datetime.now().isoformat(), playlist_id, user_id)
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_playlists(user_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM playlists WHERE user_id=? ORDER BY updated_at DESC", (user_id,)
        )
        playlists = [dict(r) for r in await cursor.fetchall()]
        for p in playlists:
            tc = await db.execute(
                "SELECT COUNT(*) FROM playlist_tracks WHERE playlist_id=?", (p["id"],)
            )
            p["track_count"] = (await tc.fetchone())[0]
        return playlists


async def get_playlist(playlist_id: int, user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM playlists WHERE id=? AND user_id=?", (playlist_id, user_id)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        p = dict(row)
        tc = await db.execute(
            "SELECT COUNT(*) FROM playlist_tracks WHERE playlist_id=?", (playlist_id,)
        )
        p["track_count"] = (await tc.fetchone())[0]
        return p


async def add_track_to_playlist(playlist_id: int, track: dict, user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        pl_cursor = await db.execute(
            "SELECT 1 FROM playlists WHERE id=? AND user_id=?", (playlist_id, user_id)
        )
        if not await pl_cursor.fetchone():
            return False
        count_cursor = await db.execute(
            "SELECT COUNT(*) FROM playlist_tracks WHERE playlist_id=?", (playlist_id,)
        )
        count = (await count_cursor.fetchone())[0]
        if count >= MAX_PLAYLIST_TRACKS:
            return False
        pos_cursor = await db.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 FROM playlist_tracks WHERE playlist_id=?", (playlist_id,)
        )
        next_pos = (await pos_cursor.fetchone())[0]
        try:
            await db.execute(
                """INSERT OR IGNORE INTO playlist_tracks
                   (playlist_id, track_id, track_title, artist_name, album_title, preview_url, cover_url, duration, position, added_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (playlist_id, track["id"], track.get("title", ""), track.get("artist", {}).get("name", ""),
                 track.get("album", {}).get("title", ""), track.get("preview", ""),
                 track.get("album", {}).get("cover_xl") or track.get("album", {}).get("cover_big") or track.get("album", {}).get("cover_medium", ""),
                 track.get("duration", 0), next_pos, datetime.now().isoformat())
            )
            await db.execute(
                "UPDATE playlists SET updated_at=? WHERE id=?", (datetime.now().isoformat(), playlist_id)
            )
            await db.commit()
            return True
        except Exception:
            return False


async def remove_track_from_playlist(playlist_id: int, track_id: int, user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        pl_cursor = await db.execute(
            "SELECT 1 FROM playlists WHERE id=? AND user_id=?", (playlist_id, user_id)
        )
        if not await pl_cursor.fetchone():
            return False
        cursor = await db.execute(
            "DELETE FROM playlist_tracks WHERE playlist_id=? AND track_id=?",
            (playlist_id, track_id)
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_playlist_tracks(playlist_id: int, user_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        pl_cursor = await db.execute(
            "SELECT 1 FROM playlists WHERE id=? AND user_id=?", (playlist_id, user_id)
        )
        if not await pl_cursor.fetchone():
            return []
        cursor = await db.execute(
            "SELECT * FROM playlist_tracks WHERE playlist_id=? ORDER BY position", (playlist_id,)
        )
        return [dict(r) for r in await cursor.fetchall()]


async def get_playlist_track_count(playlist_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM playlist_tracks WHERE playlist_id=?", (playlist_id,)
        )
        return (await cursor.fetchone())[0]


# ─── Search History ───

async def add_search_history(user_id: int, query: str, search_type: str = "track", results_count: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO search_history (user_id, query, search_type, results_count, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, query, search_type, results_count, datetime.now().isoformat())
        )
        cursor = await db.execute(
            "SELECT COUNT(*) FROM search_history WHERE user_id=?", (user_id,)
        )
        count = (await cursor.fetchone())[0]
        if count > MAX_HISTORY:
            await db.execute(
                """DELETE FROM search_history WHERE user_id=? AND id IN
                   (SELECT id FROM search_history WHERE user_id=? ORDER BY created_at ASC LIMIT ?)""",
                (user_id, user_id, count - MAX_HISTORY)
            )
        await db.commit()


async def get_search_history(user_id: int, limit: int = 20) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT DISTINCT query, search_type, MAX(created_at) as created_at
               FROM search_history WHERE user_id=?
               GROUP BY query, search_type
               ORDER BY created_at DESC LIMIT ?""",
            (user_id, limit)
        )
        return [dict(r) for r in await cursor.fetchall()]


async def clear_search_history(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM search_history WHERE user_id=?", (user_id,))
        await db.commit()


# ─── Listen History ───

async def add_listen_history(user_id: int, track: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO listen_history
               (user_id, track_id, track_title, artist_name, album_title, preview_url, cover_url, duration, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, track["id"], track.get("title", ""), track.get("artist", {}).get("name", ""),
             track.get("album", {}).get("title", ""), track.get("preview", ""),
             track.get("album", {}).get("cover_xl") or track.get("album", {}).get("cover_big") or track.get("album", {}).get("cover_medium", ""),
             track.get("duration", 0), datetime.now().isoformat())
        )
        cursor = await db.execute(
            "SELECT COUNT(*) FROM listen_history WHERE user_id=?", (user_id,)
        )
        count = (await cursor.fetchone())[0]
        if count > MAX_HISTORY:
            await db.execute(
                """DELETE FROM listen_history WHERE user_id=? AND id IN
                   (SELECT id FROM listen_history WHERE user_id=? ORDER BY created_at ASC LIMIT ?)""",
                (user_id, user_id, count - MAX_HISTORY)
            )
        await db.commit()


async def get_listen_history(user_id: int, limit: int = 20) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT DISTINCT track_id, track_title, artist_name, album_title, preview_url, cover_url, duration, MAX(created_at) as created_at
               FROM listen_history WHERE user_id=?
               GROUP BY track_id
               ORDER BY created_at DESC LIMIT ?""",
            (user_id, limit)
        )
        return [dict(r) for r in await cursor.fetchall()]


async def clear_listen_history(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM listen_history WHERE user_id=?", (user_id,))
        await db.commit()


# ─── Settings ───

async def get_user_settings(user_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM user_settings WHERE user_id=?", (user_id,))
        row = await cursor.fetchone()
        if not row:
            await db.execute("INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)", (user_id,))
            await db.commit()
            cursor = await db.execute("SELECT * FROM user_settings WHERE user_id=?", (user_id,))
            row = await cursor.fetchone()
        return dict(row) if row else {"notifications": 1, "auto_play": 0, "quality": "standard"}


async def update_user_setting(user_id: int, key: str, value):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE user_settings SET {key}=? WHERE user_id=?", (value, user_id)
        )
        await db.commit()


# ─── Stats ───

async def get_user_stats(user_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        fav_c = await db.execute("SELECT COUNT(*) FROM favorites WHERE user_id=?", (user_id,))
        favorites = (await fav_c.fetchone())[0]
        pl_c = await db.execute("SELECT COUNT(*) FROM playlists WHERE user_id=?", (user_id,))
        playlists = (await pl_c.fetchone())[0]
        hist_c = await db.execute("SELECT COUNT(*) FROM listen_history WHERE user_id=?", (user_id,))
        listens = (await hist_c.fetchone())[0]
        search_c = await db.execute("SELECT COUNT(*) FROM search_history WHERE user_id=?", (user_id,))
        searches = (await search_c.fetchone())[0]
        return {
            "favorites": favorites,
            "playlists": playlists,
            "listens": listens,
            "searches": searches,
        }
