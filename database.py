import aiosqlite
from datetime import datetime
from config import DB_PATH


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                city TEXT DEFAULT 'Москва',
                latitude REAL DEFAULT 55.7558,
                longitude REAL DEFAULT 37.6173,
                timezone TEXT DEFAULT 'Europe/Moscow',
                prayer_notifications INTEGER DEFAULT 0,
                daily_summary INTEGER DEFAULT 0,
                created_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                category TEXT DEFAULT 'other',
                remind_at TEXT NOT NULL,
                repeat_type TEXT DEFAULT NULL,
                created_at TEXT NOT NULL,
                done INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        await db.commit()


async def register_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, created_at) VALUES (?, ?)",
            (user_id, datetime.now().isoformat())
        )
        await db.commit()


async def get_user(user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def update_user_city(user_id: int, city: str, lat: float, lon: float, tz: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET city=?, latitude=?, longitude=?, timezone=? WHERE user_id=?",
            (city, lat, lon, tz, user_id)
        )
        await db.commit()


async def set_prayer_notifications(user_id: int, enabled: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET prayer_notifications=? WHERE user_id=?",
            (1 if enabled else 0, user_id)
        )
        await db.commit()


async def set_daily_summary(user_id: int, enabled: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET daily_summary=? WHERE user_id=?",
            (1 if enabled else 0, user_id)
        )
        await db.commit()


async def add_task(user_id: int, text: str, remind_at: str, category: str = "other", repeat_type: str = None) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO tasks (user_id, text, category, remind_at, repeat_type, created_at) VALUES (?,?,?,?,?,?)",
            (user_id, text, category, remind_at, repeat_type, datetime.now().isoformat())
        )
        await db.commit()
        return cursor.lastrowid


async def get_pending_tasks(user_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM tasks WHERE user_id=? AND done=0 ORDER BY remind_at",
            (user_id,)
        )
        return [dict(r) for r in await cursor.fetchall()]


async def get_tasks_by_category(user_id: int, category: str) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM tasks WHERE user_id=? AND category=? AND done=0 ORDER BY remind_at",
            (user_id, category)
        )
        return [dict(r) for r in await cursor.fetchall()]


async def get_all_pending_tasks() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM tasks WHERE done=0 ORDER BY remind_at"
        )
        return [dict(r) for r in await cursor.fetchall()]


async def get_today_tasks(user_id: int) -> list:
    today = datetime.now().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM tasks WHERE user_id=? AND done=0 AND remind_at LIKE ? ORDER BY remind_at",
            (user_id, f"{today}%")
        )
        return [dict(r) for r in await cursor.fetchall()]


async def mark_done(task_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tasks SET done=1 WHERE id=?", (task_id,))
        await db.commit()


async def delete_task(task_id: int, user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM tasks WHERE id=? AND user_id=?", (task_id, user_id)
        )
        await db.commit()
        return cursor.rowcount > 0


async def delete_all_done(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM tasks WHERE user_id=? AND done=1", (user_id,)
        )
        await db.commit()
        return cursor.rowcount


async def get_users_with_prayer() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE prayer_notifications=1"
        )
        return [dict(r) for r in await cursor.fetchall()]


async def get_users_with_daily() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE daily_summary=1"
        )
        return [dict(r) for r in await cursor.fetchall()]


async def get_stats(user_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM tasks WHERE user_id=? AND done=0", (user_id,)
        )
        pending = (await cursor.fetchone())[0]
        cursor = await db.execute(
            "SELECT COUNT(*) FROM tasks WHERE user_id=? AND done=1", (user_id,)
        )
        done = (await cursor.fetchone())[0]
        today = datetime.now().strftime("%Y-%m-%d")
        cursor = await db.execute(
            "SELECT COUNT(*) FROM tasks WHERE user_id=? AND done=0 AND remind_at LIKE ?",
            (user_id, f"{today}%")
        )
        today_count = (await cursor.fetchone())[0]
        return {"pending": pending, "done": done, "today": today_count}


async def get_last_task_id(user_id: int) -> int | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id FROM tasks WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else None


async def stop_task_repeat(task_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tasks SET repeat_type='none' WHERE id=?", (task_id,))
        await db.commit()
