import aiosqlite

DB_FILE = "tts_settings.db"

async def setup_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                voice TEXT,
                pitch REAL,
                rate REAL,
                is_nya INTEGER DEFAULT 0,
            )
        ''')
        await db.commit()

async def get_user_settings(user_id):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT voice, pitch, rate, is_nya FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {"voice": row[0], "pitch": row[1], "rate": row[2], "is_nya": bool(row[3])}
            else:
                return {"voice": "ko-KR-Wavenet-A", "pitch": 0.0, "rate": 1.0, "is_nya": False}

async def save_user_setting(user_id, voice, pitch, rate, is_nya):
    async with aiosqlite.connect(DB_FILE) as db:
        nya_val = 1 if is_nya else 0
        await db.execute('''
                INSERT OR REPLACE INTO users (user_id, voice, pitch, rate, is_nya)
                VALUES (?, ?, ?, ?, ?)
                ''', (user_id, voice, pitch, rate, nya_val))
        await db.commit()