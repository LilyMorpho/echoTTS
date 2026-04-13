import aiosqlite

DB_FILE = "tts_settings_beta.db"

async def setup_db():
    async with aiosqlite.connect("tts_settings.db") as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                voice TEXT,
                pitch REAL,
                rate REAL
            )
        ''')
        await db.commit()

async def get_user_settings(user_id):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT voice, pitch, rate FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {"voice": row[0], "pitch": row[1], "rate": row[2]}
            else:
                return {"voice": "ko-KR-Wavenet-A", "pitch": 0.0, "rate": 1.0}

async def save_user_setting(user_id, voice, pitch, rate):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('''
                INSERT OR REPLACE INTO users (user_id, voice, pitch, rate)
                VALUES (?, ?, ?, ?)
                ''', (user_id, voice, pitch, rate))
        await db.commit()