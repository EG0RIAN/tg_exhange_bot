import os
import httpx
import asyncio
import json
import aioredis
from src.db import get_pg_pool

RAPIRA_API_URL = os.getenv("RAPIRA_API_URL", "https://rapira.net/api/v2/rates")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]

async def get_redis():
    return await aioredis.create_redis_pool((REDIS_HOST, REDIS_PORT), minsize=1, maxsize=5)

async def fetch_rapira_rates(pairs: list[str]):
    params = {"pairs": ",".join(pairs)}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(RAPIRA_API_URL, params=params)
        resp.raise_for_status()
        return resp.json()

async def get_rates(pairs: list[str], bot=None):
    redis = await get_redis()
    rates = {}
    missed = []
    for pair in pairs:
        key = f"rapira:{pair}"
        cached = await redis.get(key)
        if cached:
            rates[pair] = json.loads(cached)
        else:
            missed.append(pair)
    if missed:
        try:
            rapira_data = await fetch_rapira_rates(missed)
            for pair in missed:
                if pair in rapira_data:
                    await redis.set(f"rapira:{pair}", json.dumps(rapira_data[pair]), expire=55)
                    rates[pair] = rapira_data[pair]
        except Exception as e:
            # fallback: берем из БД
            pool = await get_pg_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch("SELECT pair, ask, bid FROM rates WHERE pair = ANY($1)", missed)
                for row in rows:
                    rates[row["pair"]] = {"ask": str(row["ask"]), "bid": str(row["bid"])}
            # alert в админ-чат
            if bot and ADMIN_IDS:
                for admin_id in ADMIN_IDS:
                    await bot.send_message(admin_id, f"[ALERT] Rapira API недоступен: {e}")
    redis.close()
    await redis.wait_closed()
    return rates 