from src.db import get_pg_pool
from aiogram import Bot

async def get_all_user_ids():
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT tg_id FROM users WHERE is_blocked=false")
        return [row["tg_id"] for row in rows]

async def broadcast_message(bot: Bot, text: str):
    user_ids = await get_all_user_ids()
    for uid in user_ids:
        try:
            await bot.send_message(uid, text)
        except Exception:
            pass  # ignore errors for blocked users 