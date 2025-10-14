import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

PG_HOST = os.getenv("POSTGRES_HOST", "localhost")
PG_PORT = int(os.getenv("POSTGRES_PORT", 5432))
PG_DB = os.getenv("POSTGRES_DB", "exchange")
PG_USER = os.getenv("POSTGRES_USER", "exchange")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "exchange")

# Глобальный пул подключений
_pg_pool = None

async def get_pg_pool():
    """Получает глобальный пул подключений (singleton)"""
    global _pg_pool
    if _pg_pool is None:
        _pg_pool = await asyncpg.create_pool(
            host=PG_HOST,
            port=PG_PORT,
            user=PG_USER,
            password=PG_PASSWORD,
            database=PG_DB,
            min_size=2,
            max_size=20,  # Увеличен лимит
        )
    return _pg_pool

async def create_order(pool, user_id, pair, amount, payout_method, contact, rate_snapshot=None):
    async with pool.acquire() as conn:
        result = await conn.fetchrow(
            """
            INSERT INTO orders (user_id, pair, amount, payout_method, contact, rate_snapshot)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
            """,
            user_id, pair, amount, payout_method, contact, rate_snapshot
        )
        return result['id']

async def start_live_chat(pool, user_id):
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO live_chats (user_id, started_at, is_active)
            VALUES ($1, now(), true)
            ON CONFLICT (user_id) DO UPDATE SET is_active=true, started_at=now()
            """,
            user_id
        )

async def close_live_chat(pool, user_id):
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE live_chats SET is_active=false WHERE user_id=$1",
            user_id
        )

async def is_live_chat_active(pool, user_id):
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT is_active FROM live_chats WHERE user_id=$1", user_id)
        return row and row["is_active"]

async def get_active_live_chat_users(pool):
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT user_id FROM live_chats WHERE is_active=true")
        return [row["user_id"] for row in rows]

async def register_user(pool, tg_id: int, first_name: str = None, username: str = None, lang: str = 'ru'):
    """Регистрирует нового пользователя в базе данных"""
    async with pool.acquire() as conn:
        # Проверяем, существует ли пользователь
        existing_user = await conn.fetchrow("SELECT id FROM users WHERE tg_id = $1", tg_id)

        if existing_user:
            # Пользователь уже существует, обновляем информацию
            await conn.execute("""
                UPDATE users
                SET first_name = $1, username = $2, lang = $3
                WHERE tg_id = $4
            """, first_name, username, lang, tg_id)
            return existing_user['id']
        else:
            # Создаем нового пользователя
            user_id = await conn.fetchval("""
                INSERT INTO users (tg_id, first_name, username, lang)
                VALUES ($1, $2, $3, $4)
                RETURNING id
            """, tg_id, first_name, username, lang)
            return user_id

async def get_or_create_user(pool, tg_id: int, first_name: str = None, username: str = None, lang: str = 'ru'):
    """Получает пользователя из БД или создает нового"""
    async with pool.acquire() as conn:
        user = await conn.fetchrow("""
            SELECT id, tg_id, first_name, username, lang, is_blocked, created_at
            FROM users WHERE tg_id = $1
        """, tg_id)

        if user:
            # Обновляем информацию пользователя
            await conn.execute("""
                UPDATE users
                SET first_name = $1, username = $2, lang = $3
                WHERE tg_id = $4
            """, first_name, username, lang, tg_id)
            return user
        else:
            # Создаем нового пользователя
            user_id = await conn.fetchval("""
                INSERT INTO users (tg_id, first_name, username, lang)
                VALUES ($1, $2, $3, $4)
                RETURNING id
            """, tg_id, first_name, username, lang)

            # Возвращаем созданного пользователя
            return await conn.fetchrow("""
                SELECT id, tg_id, first_name, username, lang, is_blocked, created_at
                FROM users WHERE id = $1
            """, user_id) 