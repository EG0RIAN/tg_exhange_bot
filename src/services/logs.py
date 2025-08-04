import os
from src.db import get_pg_pool

async def get_logs(level="error", limit=50):
    # Если есть таблица logs, используем её, иначе читаем из файла
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT created_at, level, message FROM logs WHERE level=$1 ORDER BY created_at DESC LIMIT $2", level, limit)
        return [dict(row) for row in rows] 